# workers/views.py
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from .models import WorkerProfile, WorkerService
from .serializers import (
    WorkerProfileListSerializer, 
    WorkerProfileDetailSerializer,
    WorkerProfileCreateUpdateSerializer,
    WorkerServiceSerializer
)
from services.models import ServiceCategory


class WorkerListView(generics.ListAPIView):
    """
    List workers with filtering and search (for client home screen)
    قائمة العمال مع الفلترة والبحث (لشاشة العميل الرئيسية)
    """
    queryset = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True
    ).select_related('profile__user').prefetch_related('services__category')
    
    serializer_class = WorkerProfileListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search fields
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'bio', 'service_area', 'services__category__name'
    ]
    
    # Filter fields
    filterset_fields = ['is_verified', 'is_online']
    
    # Ordering options
    ordering_fields = ['average_rating', 'total_jobs_completed', 'last_seen']
    ordering = ['-is_online', '-average_rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by service category
        category = self.request.query_params.get('category', None)
        if category:
            if category.isdigit():
                # Filter by category ID
                queryset = queryset.filter(services__category__id=category)
            else:
                # Filter by category name
                queryset = queryset.filter(
                    Q(services__category__name__icontains=category) |
                    Q(services__category__name_ar__icontains=category)
                )
        
        # Filter by area/location
        area = self.request.query_params.get('area', None)
        if area:
            queryset = queryset.filter(
                Q(service_area__icontains=area)
            )
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(services__base_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(services__base_price__lte=max_price)
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating', None)
        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)
        
        # Filter by availability (online now)
        online_only = self.request.query_params.get('online_only', None)
        if online_only and online_only.lower() == 'true':
            queryset = queryset.filter(is_online=True)
        
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Custom sorting options
        sort_by = request.query_params.get('sort_by', None)
        if sort_by == 'price_asc':
            # Sort by minimum service price ascending
            queryset = queryset.order_by('services__base_price')
        elif sort_by == 'price_desc':
            # Sort by maximum service price descending
            queryset = queryset.order_by('-services__base_price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        elif sort_by == 'experience':
            queryset = queryset.order_by('-total_jobs_completed')
        elif sort_by == 'nearest':
            # TODO: Implement distance-based sorting
            pass
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


class WorkerDetailView(generics.RetrieveAPIView):
    """
    Get detailed worker profile (for worker detail screen)
    الحصول على ملف العامل المفصل (لشاشة تفاصيل العامل)
    """
    queryset = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True
    ).select_related('profile__user').prefetch_related(
        'services__category', 'gallery', 'experiences'
    )
    
    serializer_class = WorkerProfileDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


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
            worker__is_available=True
        ).select_related('category')


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_search_filters(request):
    """
    Get available filter options for Flutter worker search
    الحصول على خيارات الفلترة المتاحة لبحث العمال في Flutter
    """
    # Get available service categories (matching Flutter categories list)
    categories = ServiceCategory.objects.filter(
        is_active=True,
        workerservice__isnull=False
    ).distinct().values('name', 'name_ar').order_by('name')
    
    # Convert to Flutter-compatible format
    flutter_categories = ['Toutes Catégories'] + [cat['name'] for cat in categories]
    
    # Get available areas (matching Flutter nouakchottAreas list)
    areas = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True,
        service_area__isnull=False
    ).values_list('service_area', flat=True).distinct()
    
    # Clean and format areas for Flutter
    unique_areas = []
    for area in areas:
        if area:
            # Extract main area name (before comma if exists)
            main_area = area.split(',')[0].strip()
            if main_area and main_area not in unique_areas:
                unique_areas.append(main_area)
    
    flutter_areas = ['Toutes Zones'] + sorted(unique_areas)
    
    # Get price range statistics
    price_stats = WorkerService.objects.filter(
        is_active=True,
        worker__is_available=True
    ).aggregate(
        min_price=models.Min('base_price'),
        max_price=models.Max('base_price'),
        avg_price=models.Avg('base_price')
    )
    
    # Flutter-compatible sort options (exactly matching your Flutter code)
    sort_options = [
        'nearest',    # الأقرب (مهم جداً)
        'price_asc',  # السعر أرخص أولاً  
        'price_desc', # السعر أغلى أولاً
        'rating'      # أعلى تقييم
    ]
    
    return Response({
        # Flutter-compatible filter data
        'categories': flutter_categories,
        'nouakchottAreas': flutter_areas,  # Matching Flutter variable name
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
    from django.db.models import Count, Sum
    
    # Basic statistics
    total_workers = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True
    ).count()
    
    online_workers = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True,
        is_online=True
    ).count()
    
    verified_workers = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True,
        is_verified=True
    ).count()
    
    # Average rating across all workers
    avg_rating = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True,
        average_rating__gt=0
    ).aggregate(avg_rating=models.Avg('average_rating'))['avg_rating']
    
    # Total jobs completed
    total_jobs = WorkerProfile.objects.filter(
        is_available=True,
        profile__onboarding_completed=True
    ).aggregate(total_jobs=Sum('total_jobs_completed'))['total_jobs']
    
    # Top categories by worker count  
    top_categories = ServiceCategory.objects.filter(
        workerservice__is_active=True,
        workerservice__worker__is_available=True,
        workerservice__worker__profile__onboarding_completed=True
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


# For future use - worker profile management endpoints
class WorkerProfileCreateView(generics.CreateAPIView):
    """
    Create worker profile (for onboarding completion)
    إنشاء ملف العامل (لإكمال التسجيل)
    """
    queryset = WorkerProfile.objects.all()
    serializer_class = WorkerProfileCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Ensure the user has a worker profile and completed onboarding
        profile = self.request.user.profile
        if profile.role != 'worker':
            raise ValidationError("Only workers can create worker profiles")
        
        serializer.save(profile=profile)


class WorkerProfileUpdateView(generics.UpdateAPIView):
    """
    Update worker profile (for settings/profile edit)
    تحديث ملف العامل (للإعدادات/تعديل الملف)
    """
    queryset = WorkerProfile.objects.all()
    serializer_class = WorkerProfileCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.profile.worker_profile