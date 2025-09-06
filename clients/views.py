# clients/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import ClientProfile, FavoriteWorker, ClientSettings
from .serializers import (
    ClientProfileSerializer,
    ClientBasicSerializer,
    FavoriteWorkerSerializer,
    FavoriteWorkerCreateSerializer,
    ClientStatsSerializer,
    ClientSettingsSerializer
)
from workers.models import WorkerProfile
from accounts.models import Profile


class ClientProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update client profile with partial update support
    عرض أو تحديث ملف العميل مع دعم التحديث الجزئي
    """
    serializer_class = ClientProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            raise PermissionDenied("Only clients can access this endpoint")
        
        # Get or create client profile
        client_profile, created = ClientProfile.objects.get_or_create(
            profile=self.request.user.profile,
            defaults={
                'bio': '',
                'preferred_language': 'fr',
                'notifications_enabled': True,
                'email_notifications': True,
                'sms_notifications': True,
            }
        )
        
        # Create settings if not exist
        ClientSettings.objects.get_or_create(
            client=self.request.user.profile,
            defaults={
                'push_notifications': True,
                'email_notifications': True,
                'theme_preference': 'auto',
                'language': 'fr',
                'profile_visibility': 'workers_only',
                'auto_detect_location': True,
                'search_radius_km': 10,
            }
        )
        
        return client_profile
    
    def perform_update(self, serializer):
        """Update client profile and refresh stats"""
        client_profile = serializer.save()
        # Update statistics when profile is updated
        client_profile.update_stats()


class FavoriteWorkersListView(generics.ListAPIView):
    """
    List client's favorite workers with filtering
    قائمة العمال المفضلين للعميل مع الفلترة
    """
    serializer_class = FavoriteWorkerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            return FavoriteWorker.objects.none()
        
        queryset = FavoriteWorker.objects.filter(
            client=self.request.user.profile
        ).select_related(
            'worker__profile__user'
        ).prefetch_related(
            'worker__services__category'
        )
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category and category != 'Tous':
            queryset = queryset.filter(
                worker__services__category__name__icontains=category
            )
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(worker__profile__user__first_name__icontains=search) |
                Q(worker__profile__user__last_name__icontains=search) |
                Q(worker__profile__user__username__icontains=search)
            )
        
        # Sort options
        sort_by = self.request.query_params.get('sort_by', 'latest')
        if sort_by == 'rating_high':
            queryset = queryset.order_by('-worker__average_rating')
        elif sort_by == 'experience':
            queryset = queryset.order_by('-worker__total_jobs_completed')
        elif sort_by == 'online':
            queryset = queryset.order_by('-worker__is_online', '-added_at')
        elif sort_by == 'times_hired':
            queryset = queryset.order_by('-times_hired')
        else:  # latest
            queryset = queryset.order_by('-added_at')
        
        return queryset


class FavoriteWorkerCreateView(generics.CreateAPIView):
    """
    Add worker to favorites
    إضافة عامل للمفضلة
    """
    serializer_class = FavoriteWorkerCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            raise PermissionDenied("Only clients can add favorites")
        
        favorite = serializer.save()
        
        # Optional: Send notification to worker about being favorited
        # (implement if needed later)
        
        return favorite


class FavoriteWorkerDeleteView(generics.DestroyAPIView):
    """
    Remove worker from favorites
    إزالة عامل من المفضلة
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'worker_id'
    
    def get_queryset(self):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            return FavoriteWorker.objects.none()
        
        return FavoriteWorker.objects.filter(client=self.request.user.profile)
    
    def get_object(self):
        worker_id = self.kwargs.get('worker_id')
        try:
            return FavoriteWorker.objects.get(
                client=self.request.user.profile,
                worker_id=worker_id
            )
        except FavoriteWorker.DoesNotExist:
            raise NotFound("Worker not found in favorites")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_favorite_worker(request, worker_id):
    """
    Toggle worker favorite status (add/remove)
    تبديل حالة العامل المفضل (إضافة/إزالة)
    """
    # Ensure user is a client
    if request.user.profile.role != 'client':
        raise PermissionDenied("Only clients can manage favorites")
    
    # Check if worker exists
    try:
        worker = WorkerProfile.objects.get(id=worker_id, is_available=True)
    except WorkerProfile.DoesNotExist:
        raise NotFound("Worker not found or not available")
    
    # Check current favorite status
    favorite, created = FavoriteWorker.objects.get_or_create(
        client=request.user.profile,
        worker=worker,
        defaults={'notes': ''}
    )
    
    if created:
        # Added to favorites
        return Response({
            'message': 'Worker added to favorites',
            'is_favorite': True,
            'worker_name': favorite.worker_full_name
        }, status=status.HTTP_201_CREATED)
    else:
        # Remove from favorites
        favorite.delete()
        return Response({
            'message': 'Worker removed from favorites',
            'is_favorite': False,
            'worker_name': favorite.worker_full_name
        }, status=status.HTTP_200_OK)


class ClientStatsView(generics.RetrieveAPIView):
    """
    Get client statistics
    إحصائيات العميل
    """
    serializer_class = ClientStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            raise PermissionDenied("Only clients can access statistics")
        
        # Get or create client profile
        client_profile, created = ClientProfile.objects.get_or_create(
            profile=self.request.user.profile
        )
        
        # Update statistics before returning
        client_profile.update_stats()
        
        return client_profile


class ClientSettingsView(generics.RetrieveUpdateAPIView):
    """
    Get or update client settings with partial update support
    عرض أو تحديث إعدادات العميل مع دعم التحديث الجزئي
    """
    serializer_class = ClientSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            raise PermissionDenied("Only clients can access settings")
        
        # Get or create client settings
        settings, created = ClientSettings.objects.get_or_create(
            client=self.request.user.profile,
            defaults={
                'push_notifications': True,
                'email_notifications': True,
                'theme_preference': 'auto',
                'language': 'fr',
                'profile_visibility': 'workers_only',
                'auto_detect_location': True,
                'search_radius_km': 10,
            }
        )
        
        return settings


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_worker_favorite_status(request, worker_id):
    """
    Check if worker is in client's favorites
    التحقق من وجود العامل في مفضلة العميل
    """
    # Ensure user is a client
    if request.user.profile.role != 'client':
        raise PermissionDenied("Only clients can check favorite status")
    
    is_favorite = FavoriteWorker.objects.filter(
        client=request.user.profile,
        worker_id=worker_id
    ).exists()
    
    return Response({
        'is_favorite': is_favorite,
        'worker_id': worker_id
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def client_dashboard_data(request):
    """
    Get client dashboard summary data
    بيانات لوحة التحكم للعميل
    """
    # Ensure user is a client
    if request.user.profile.role != 'client':
        raise PermissionDenied("Only clients can access dashboard")
    
    # Get or create client profile
    client_profile, created = ClientProfile.objects.get_or_create(
        profile=request.user.profile
    )
    
    # Update stats
    client_profile.update_stats()
    
    # Get recent activity counts
    from tasks.models import ServiceRequest
    
    recent_tasks = ServiceRequest.objects.filter(
        client=request.user.profile,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    )
    
    # Get favorite workers count
    favorite_workers_count = FavoriteWorker.objects.filter(
        client=request.user.profile
    ).count()
    
    dashboard_data = {
        'profile': {
            'full_name': client_profile.full_name,
            'member_since': client_profile.member_since,
            'is_verified': client_profile.is_verified,
            'profile_image_url': client_profile.profile_image.url if client_profile.profile_image else None
        },
        'stats': {
            'total_tasks': client_profile.total_tasks_published,
            'completed_tasks': client_profile.total_tasks_completed,
            'success_rate': client_profile.success_rate,
            'total_spent': float(client_profile.total_amount_spent),
            'recent_tasks_count': recent_tasks.count()
        },
        'activity': {
            'favorite_workers': favorite_workers_count,
            'active_tasks': ServiceRequest.objects.filter(
                client=request.user.profile,
                status__in=['published', 'active', 'work_completed']
            ).count()
        }
    }
    
    return Response(dashboard_data)