# clients/views.py - مُصحح للنظام الجديد
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import FavoriteWorker, ClientSettings
from .serializers import (
    ClientProfileSerializer,
    FavoriteWorkerSerializer,
    FavoriteWorkerCreateSerializer,
    ClientSettingsSerializer
)
from users.models import User


class ClientProfileView(generics.RetrieveUpdateAPIView):
   """
   Get or update client profile
   عرض أو تحديث ملف العميل
   """
   serializer_class = ClientProfileSerializer
   permission_classes = [permissions.IsAuthenticated]
   
   def get_object(self):
       # Ensure user is a client
       if self.request.user.role != 'client':
           raise PermissionDenied("Only clients can access this endpoint")
       
       # Return User object (not ClientProfile)
       return self.request.user
   
   
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
        if self.request.user.role != 'client':
            return FavoriteWorker.objects.none()
        
        queryset = FavoriteWorker.objects.filter(
            client=self.request.user
        ).select_related(
            'worker'
        ).prefetch_related(
            'worker__worker_services__category'
        )
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category and category != 'Tous':
            queryset = queryset.filter(
                worker__worker_services__category__name__icontains=category
            )
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(worker__first_name__icontains=search) |
                Q(worker__last_name__icontains=search)
            )
        
        # Sort options
        sort_by = self.request.query_params.get('sort_by', 'latest')
        if sort_by == 'rating_high':
            queryset = queryset.filter(worker__worker_profile__isnull=False).order_by('-worker__worker_profile__average_rating')
        elif sort_by == 'experience':
            queryset = queryset.filter(worker__worker_profile__isnull=False).order_by('-worker__worker_profile__total_jobs_completed')
        elif sort_by == 'online':
            queryset = queryset.filter(worker__worker_profile__isnull=False).order_by('-worker__worker_profile__is_online', '-added_at')
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
        if self.request.user.role != 'client':
            raise PermissionDenied("Only clients can add favorites")
        
        favorite = serializer.save()
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
        if self.request.user.role != 'client':
            return FavoriteWorker.objects.none()
        
        return FavoriteWorker.objects.filter(client=self.request.user)
    
    def get_object(self):
        worker_id = self.kwargs.get('worker_id')
        try:
            return FavoriteWorker.objects.get(
                client=self.request.user,
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
    if request.user.role != 'client':
        raise PermissionDenied("Only clients can manage favorites")
    
    # Check if worker exists
    try:
        worker = User.objects.get(id=worker_id, role='worker', is_verified=True)
    except User.DoesNotExist:
        raise NotFound("Worker not found or not available")
    
    # Check current favorite status
    favorite, created = FavoriteWorker.objects.get_or_create(
        client=request.user,
        worker=worker,
        defaults={'notes': ''}
    )
    
    if created:
        # Added to favorites
        return Response({
            'message': 'Worker added to favorites',
            'is_favorite': True,
            'worker_name': worker.get_full_name()
        }, status=status.HTTP_201_CREATED)
    else:
        # Remove from favorites
        favorite.delete()
        return Response({
            'message': 'Worker removed from favorites',
            'is_favorite': False,
            'worker_name': worker.get_full_name()
        }, status=status.HTTP_200_OK)


class ClientSettingsView(generics.RetrieveUpdateAPIView):
    """
    Get or update client settings with partial update support
    عرض أو تحديث إعدادات العميل مع دعم التحديث الجزئي
    """
    serializer_class = ClientSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a client
        if self.request.user.role != 'client':
            raise PermissionDenied("Only clients can access settings")
        
        # Get or create client settings
        settings, created = ClientSettings.objects.get_or_create(
            client=self.request.user,
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
def client_stats(request):
    """
    Get client statistics
    إحصائيات العميل
    """
    # Ensure user is a client
    if request.user.role != 'client':
        raise PermissionDenied("Only clients can access statistics")
    
    # Get client profile data
    client_profile = getattr(request.user, 'client_profile', None)
    
    # Get tasks data
    from tasks.models import ServiceRequest
    
    # Basic task counts
    published_tasks = ServiceRequest.objects.filter(client=request.user).count()
    completed_tasks = ServiceRequest.objects.filter(client=request.user, status='completed').count()
    cancelled_tasks = ServiceRequest.objects.filter(client=request.user, status='cancelled').count()
    active_tasks = ServiceRequest.objects.filter(
        client=request.user, 
        status__in=['published', 'active', 'work_completed']
    ).count()
    
    # Financial calculations
    completed_task_objs = ServiceRequest.objects.filter(client=request.user, status='completed')
    total_spent = sum(task.budget for task in completed_task_objs) if completed_task_objs.exists() else 0
    average_task_value = total_spent / completed_tasks if completed_tasks > 0 else 0
    
    # Favorite workers
    favorite_workers_count = FavoriteWorker.objects.filter(client=request.user).count()
    most_hired_worker = FavoriteWorker.objects.filter(
        client=request.user
    ).order_by('-times_hired').first()
    
    # Success rate
    success_rate = (completed_tasks / published_tasks * 100) if published_tasks > 0 else 0
    
    # Days active
    days_active = (timezone.now().date() - request.user.date_joined.date()).days
    
    stats_data = {
        'published_tasks': published_tasks,
        'completed_tasks': completed_tasks,
        'cancelled_tasks': cancelled_tasks,
        'active_tasks': active_tasks,
        'total_spent': f"{total_spent:.2f}",
        'average_task_value': f"{average_task_value:.2f}",
        'favorite_workers_count': favorite_workers_count,
        'most_hired_worker': {
            'name': most_hired_worker.worker.get_full_name(),
            'times_hired': most_hired_worker.times_hired,
            'total_spent': float(most_hired_worker.total_spent_with_worker)
        } if most_hired_worker else None,
        'success_rate': round(success_rate, 1),
        'member_since': request.user.date_joined.strftime("%B %Y"),
        'days_active': days_active
    }
    
    return Response(stats_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_worker_favorite_status(request, worker_id):
    """
    Check if worker is in client's favorites
    التحقق من وجود العامل في مفضلة العميل
    """
    # Ensure user is a client
    if request.user.role != 'client':
        raise PermissionDenied("Only clients can check favorite status")
    
    is_favorite = FavoriteWorker.objects.filter(
        client=request.user,
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
    if request.user.role != 'client':
        raise PermissionDenied("Only clients can access dashboard")
    
    # Get client profile data
    client_profile = getattr(request.user, 'client_profile', None)
    
    # Get recent activity counts
    from tasks.models import ServiceRequest
    
    recent_tasks = ServiceRequest.objects.filter(
        client=request.user,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    )
    
    # Get favorite workers count
    favorite_workers_count = FavoriteWorker.objects.filter(
        client=request.user
    ).count()
    
    dashboard_data = {
        'profile': {
            'full_name': request.user.get_full_name() or request.user.phone,
            'member_since': request.user.date_joined.strftime("%B %Y"),
            'is_verified': request.user.is_verified,
            'profile_image_url': client_profile.profile_image.url if client_profile and client_profile.profile_image else None
        },
        'stats': {
            'total_tasks': client_profile.total_tasks_published if client_profile else 0,
            'completed_tasks': client_profile.total_tasks_completed if client_profile else 0,
            'success_rate': client_profile.success_rate if client_profile else 0,
            'total_spent': float(client_profile.total_amount_spent) if client_profile else 0.0,
            'recent_tasks_count': recent_tasks.count()
        },
        'activity': {
            'favorite_workers': favorite_workers_count,
            'active_tasks': ServiceRequest.objects.filter(
                client=request.user,
                status__in=['published', 'active', 'work_completed']
            ).count()
        }
    }
    
    return Response(dashboard_data)