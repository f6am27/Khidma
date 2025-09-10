# workers/views.py - النسخة النهائية الكاملة
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Min, Max, Sum, Count
from math import radians, cos, sin, asin, sqrt
from .models import WorkerService, WorkerSettings
from .serializers import (
    WorkerProfileListSerializer, 
    WorkerProfileDetailSerializer,
    WorkerProfileSerializer,
    WorkerProfileUpdateSerializer,
    WorkerServiceSerializer,
    WorkerSettingsSerializer
)
from users.models import User
from services.models import ServiceCategory


class WorkerListView(generics.ListAPIView):
    """
    List workers with filtering and search (for client home screen)
    قائمة العمال مع الفلترة والبحث (لشاشة العميل الرئيسية)
    """
    queryset = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True
    ).select_related('worker_profile').prefetch_related('worker_services__category')
    
    serializer_class = WorkerProfileListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = [
        'first_name', 'last_name', 'phone',
        'worker_profile__bio', 'worker_profile__service_area', 
        'worker_services__category__name'
    ]
    
    # Filter fields
    filterset_fields = ['worker_profile__is_verified', 'worker_profile__is_online']
    
    # Ordering options
    ordering_fields = ['worker_profile__average_rating', 'worker_profile__total_jobs_completed', 'worker_profile__last_seen']
    ordering = ['-worker_profile__is_online', '-worker_profile__average_rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by service category
        category = self.request.query_params.get('category', None)
        if category and category not in ['Toutes Catégories', 'All Categories']:
            if category.isdigit():
                queryset = queryset.filter(worker_services__category__id=category)
            else:
                queryset = queryset.filter(
                    Q(worker_services__category__name__icontains=category) |
                    Q(worker_services__category__name_ar__icontains=category)
                )
        
        # Filter by area/location
        area = self.request.query_params.get('area', None)
        if area and area not in ['Toutes Zones', 'All Areas']:
            queryset = queryset.filter(
                Q(worker_profile__service_area__icontains=area)
            )
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(worker_services__base_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(worker_services__base_price__lte=max_price)
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating', None)
        if min_rating:
            queryset = queryset.filter(worker_profile__average_rating__gte=min_rating)
        
        # Filter by availability (online now)
        online_only = self.request.query_params.get('online_only', None)
        if online_only and online_only.lower() == 'true':
            queryset = queryset.filter(worker_profile__is_online=True)
        
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Custom sorting options
        sort_by = request.query_params.get('sort_by', None)
        
        if sort_by == 'price_asc':
            queryset = queryset.order_by('worker_services__base_price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-worker_services__base_price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-worker_profile__average_rating')
        elif sort_by == 'experience':
            queryset = queryset.order_by('-worker_profile__total_jobs_completed')
        elif sort_by == 'nearest':
            # Distance-based sorting
            client_lat = request.query_params.get('lat')
            client_lng = request.query_params.get('lng')
            
            if client_lat and client_lng:
                try:
                    client_lat = float(client_lat)
                    client_lng = float(client_lng)
                    
                    workers_with_distance = []
                    for worker in queryset:
                        if (hasattr(worker, 'worker_profile') and 
                            worker.worker_profile.latitude and worker.worker_profile.longitude):
                            distance = self.calculate_distance(
                                client_lat, client_lng,
                                float(worker.worker_profile.latitude), 
                                float(worker.worker_profile.longitude)
                            )
                            workers_with_distance.append((worker, distance))
                        else:
                            workers_with_distance.append((worker, 999))
                    
                    workers_with_distance.sort(key=lambda x: x[1])
                    queryset = [worker for worker, distance in workers_with_distance]
                    
                except (ValueError, TypeError):
                    pass
        
        # Handle pagination for sorted queryset
        if sort_by == 'nearest' and isinstance(queryset, list):
            page_size = self.get_paginator().page_size
            page_number = request.query_params.get('page', 1)
            try:
                page_number = int(page_number)
            except ValueError:
                page_number = 1
            
            start = (page_number - 1) * page_size
            end = start + page_size
            page_queryset = queryset[start:end]
            
            serializer = self.get_serializer(page_queryset, many=True)
            return Response({
                'count': len(queryset),
                'results': serializer.data
            })
        
        # Standard pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })

    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points using Haversine formula"""
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r


class WorkerDetailView(generics.RetrieveAPIView):
    """
    Get detailed worker profile (for worker detail screen)
    الحصول على ملف العامل المفصل (لشاشة تفاصيل العامل)
    """
    queryset = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True
    ).select_related('worker_profile').prefetch_related(
        'worker_services__category', 'worker_gallery'
    )
    
    serializer_class = WorkerProfileDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


class WorkerProfileView(generics.RetrieveUpdateAPIView):
    """
    Worker's own profile view and update
    عرض وتحديث ملف العامل الشخصي
    """
    serializer_class = WorkerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a worker
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can access this endpoint")
        
        return self.request.user


class WorkerProfileUpdateView(generics.UpdateAPIView):
    """
    Update worker profile (for profile edit)
    تحديث ملف العامل (لتعديل الملف)
    """
    serializer_class = WorkerProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can update worker profiles")
        return self.request.user


class WorkerServiceListView(generics.ListAPIView):
    """
    List services for a specific worker
    قائمة خدمات عامل معين
    """
    serializer_class = WorkerServiceSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        worker_id = self.kwargs.get('worker_id')
        return WorkerService.objects.filter(
            worker_id=worker_id, 
            is_active=True,
            worker__role='worker',
            worker__is_verified=True
        ).select_related('category')


class WorkerSettingsView(generics.RetrieveUpdateAPIView):
    """
    Get or update worker settings
    عرض أو تحديث إعدادات العامل
    """
    serializer_class = WorkerSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Ensure user is a worker
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can access settings")
        
        # Get or create worker settings
        settings, created = WorkerSettings.objects.get_or_create(
            worker=self.request.user,
            defaults={
                'push_notifications': True,
                'email_notifications': False,
                'sms_notifications': True,
                'theme_preference': 'auto',
                'language': 'fr',
                'auto_accept_jobs': False,
                'max_daily_jobs': 5,
                'profile_visibility': 'public',
                'travel_radius_km': 15,
                'instant_booking': True,
            }
        )
        
        return settings


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_search_filters(request):
    """
    Get available filter options for Flutter worker search
    الحصول على خيارات الفلترة المتاحة لبحث العمال في Flutter
    """
    categories = ServiceCategory.objects.filter(
        is_active=True,
        workerservice__isnull=False
    ).distinct().values('name', 'name_ar').order_by('name')
    
    flutter_categories = ['Toutes Catégories'] + [cat['name'] for cat in categories]
    
    areas = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True,
        worker_profile__service_area__isnull=False
    ).values_list('worker_profile__service_area', flat=True).distinct()
    
    unique_areas = []
    for area in areas:
        if area:
            main_area = area.split(',')[0].strip()
            if main_area and main_area not in unique_areas:
                unique_areas.append(main_area)
    
    flutter_areas = ['Toutes Zones'] + sorted(unique_areas)
    
    price_stats = WorkerService.objects.filter(
        is_active=True,
        worker__role='worker',
        worker__is_verified=True
    ).aggregate(
        min_price=Min('base_price'),
        max_price=Max('base_price'),
        avg_price=Avg('base_price')
    )
    
    sort_options = [
        'nearest',
        'price_asc',
        'price_desc',
        'rating'
    ]
    
    return Response({
        'categories': flutter_categories,
        'nouakchottAreas': flutter_areas,
        'allServices': [
            {
                'icon': 'cleaning_services',
                'name': cat['name'],
                'category': cat['name']
            } for cat in categories
        ],
        'price_range': {
            'min': int(price_stats['min_price']) if price_stats['min_price'] else 500,
            'max': int(price_stats['max_price']) if price_stats['max_price'] else 10000,
            'average': int(price_stats['avg_price']) if price_stats['avg_price'] else 2500
        },
        'sort_options': sort_options
    })


@api_view(['GET']) 
@permission_classes([AllowAny])
def worker_stats(request):
    """
    Get Flutter-compatible worker statistics
    إحصائيات العمال متوافقة مع Flutter
    """
    total_workers = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True
    ).count()
    
    online_workers = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True,
        worker_profile__is_online=True
    ).count()
    
    verified_workers = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True,
        worker_profile__is_verified=True
    ).count()
    
    avg_rating = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True,
        worker_profile__average_rating__gt=0
    ).aggregate(avg_rating=Avg('worker_profile__average_rating'))['avg_rating']
    
    total_jobs = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True
    ).aggregate(total_jobs=Sum('worker_profile__total_jobs_completed'))['total_jobs']
    
    top_categories = ServiceCategory.objects.filter(
        workerservice__is_active=True,
        workerservice__worker__role='worker',
        workerservice__worker__is_verified=True,
        workerservice__worker__onboarding_completed=True
    ).annotate(
        worker_count=Count('workerservice__worker', distinct=True)
    ).order_by('-worker_count')[:5].values('name', 'worker_count')
    
    return Response({
        'total_workers': total_workers,
        'online_workers': online_workers, 
        'verified_workers': verified_workers,
        'average_rating': round(float(avg_rating), 1) if avg_rating else 0,
        'total_jobs_completed': total_jobs or 0,
        'top_categories': list(top_categories)
    })