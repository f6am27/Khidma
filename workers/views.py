# workers/views.py - النسخة النهائية بعد إضافة APIs جديدة للمواقع

from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Min, Max, Sum, Count
from math import radians, cos, sin, asin, sqrt
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import WorkerService, WorkerSettings
from .serializers import (
    WorkerProfileListSerializer, 
    WorkerProfileDetailSerializer,
    WorkerProfileSerializer,
    WorkerProfileUpdateSerializer,
    WorkerServiceSerializer,
    WorkerSettingsSerializer,
    WorkerLocationSerializer,
    LocationToggleSerializer
)
from users.models import User
from services.models import ServiceCategory
from tasks.models import ServiceRequest
from tasks.serializers import AvailableTaskSerializer

# ==================== النسخة الأصلية ====================

class WorkerListView(generics.ListAPIView):
    queryset = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True
    ).select_related('worker_profile').prefetch_related('worker_services__category')
    
    serializer_class = WorkerProfileListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'first_name', 'last_name', 'phone',
        'worker_profile__bio', 'worker_profile__service_area', 
        'worker_services__category__name'
    ]
    
    filterset_fields = ['worker_profile__is_verified', 'worker_profile__is_online']
    
    ordering_fields = ['worker_profile__average_rating', 'worker_profile__total_jobs_completed', 'worker_profile__last_seen']
    ordering = ['-worker_profile__is_online', '-worker_profile__average_rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category', None)
        if category and category not in ['Toutes Catégories', 'All Categories']:
            if category.isdigit():
                queryset = queryset.filter(worker_services__category__id=category)
            else:
                queryset = queryset.filter(
                    Q(worker_services__category__name__icontains=category) |
                    Q(worker_services__category__name_ar__icontains=category)
                )
        
        area = self.request.query_params.get('area', None)
        if area and area not in ['Toutes Zones', 'All Areas']:
            queryset = queryset.filter(
                Q(worker_profile__service_area__icontains=area)
            )
        
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(worker_services__base_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(worker_services__base_price__lte=max_price)
        
        min_rating = self.request.query_params.get('min_rating', None)
        if min_rating:
            queryset = queryset.filter(worker_profile__average_rating__gte=min_rating)
        
        online_only = self.request.query_params.get('online_only', None)
        if online_only and online_only.lower() == 'true':
            queryset = queryset.filter(worker_profile__is_online=True)
        
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
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
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r


class WorkerDetailView(generics.RetrieveAPIView):
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
    serializer_class = WorkerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can access this endpoint")
        return self.request.user


class WorkerProfileUpdateView(generics.UpdateAPIView):
    serializer_class = WorkerProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can update worker profiles")
        return self.request.user


class WorkerServiceListView(generics.ListAPIView):
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
    serializer_class = WorkerSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can access settings")
        
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

# ==================== APIs الموقع الجديدة ====================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_location_sharing(request):
    """
    تفعيل/إلغاء مشاركة الموقع
    POST /api/users/toggle-location-sharing/
    """
    if not request.user.is_worker:
        return Response({
            "code": "not_worker",
            "detail": "هذا العضو ليس عاملاً"
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        return Response({
            "code": "profile_not_found",
            "detail": "ملف العامل غير موجود"
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LocationSharingToggleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تغيير حالة المشاركة
    new_status = worker_profile.toggle_location_sharing(
        enabled=serializer.validated_data['enabled']
    )
    
    # ✅ جديد: تحديث is_online تلقائياً
    worker_profile.is_online = new_status
    worker_profile.save(update_fields=['is_online'])
    
    return Response({
        "success": True,
        "message": f"تم {'تفعيل' if new_status else 'إلغاء'} مشاركة الموقع",
        "data": {
            "location_sharing_enabled": new_status,
            "location_status": worker_profile.location_status,
            "is_online": worker_profile.is_online,  # ✅ جديد
            "updated_at": worker_profile.location_sharing_updated_at.isoformat() if worker_profile.location_sharing_updated_at else None
        }
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_current_location(request):
    if request.user.role != 'worker':
        raise PermissionDenied("هذه الخدمة متاحة للعمال فقط")
    
    if not hasattr(request.user, 'worker_profile'):
        raise ValidationError("ملف العامل غير مكتمل")
    
    worker_profile = request.user.worker_profile
    
    if not worker_profile.location_sharing_enabled:
        return Response({'error': 'مشاركة الموقع غير مفعلة','message': 'يجب تفعيل مشاركة الموقع أولاً'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = WorkerLocationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'بيانات غير صحيحة', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    latitude = serializer.validated_data.get('current_latitude')
    longitude = serializer.validated_data.get('current_longitude') 
    accuracy = serializer.validated_data.get('location_accuracy')
    
    if latitude is None or longitude is None:
        return Response({'error': 'إحداثيات غير مكتملة','message': 'يجب تقديم خط العرض والطول'}, status=status.HTTP_400_BAD_REQUEST)
    
    success = worker_profile.update_current_location(latitude, longitude, accuracy)
    if not success:
        return Response({'error': 'فشل في التحديث','message': 'تعذر تحديث الموقع'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'success': True,
        'message': 'تم تحديث الموقع بنجاح',
        'data': {
            'current_latitude': float(worker_profile.current_latitude),
            'current_longitude': float(worker_profile.current_longitude),
            'location_accuracy': worker_profile.location_accuracy,
            'location_last_updated': worker_profile.location_last_updated,
            'location_status': worker_profile.location_status
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_location_status(request):
    if request.user.role != 'worker':
        raise PermissionDenied("هذه الخدمة متاحة للعمال فقط")
    
    if not hasattr(request.user, 'worker_profile'):
        return Response({'error': 'ملف العامل غير مكتمل'}, status=status.HTTP_400_BAD_REQUEST)
    
    worker_profile = request.user.worker_profile
    worker_profile.update_location_status()
    
    return Response({
        'success': True,
        'data': {
            'location_sharing_enabled': worker_profile.location_sharing_enabled,
            'location_status': worker_profile.location_status,
            'current_latitude': float(worker_profile.current_latitude) if worker_profile.current_latitude else None,
            'current_longitude': float(worker_profile.current_longitude) if worker_profile.current_longitude else None,
            'location_accuracy': worker_profile.location_accuracy,
            'location_last_updated': worker_profile.location_last_updated,
            'location_sharing_updated_at': worker_profile.location_sharing_updated_at,
            'is_location_fresh': worker_profile.is_location_fresh(),
            'is_currently_available': worker_profile.is_currently_available_with_location
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearby_tasks(request):
    if request.user.role != 'worker':
        raise PermissionDenied("هذه الخدمة متاحة للعمال فقط")
    
    if not hasattr(request.user, 'worker_profile'):
        return Response({'error': 'ملف العامل غير مكتمل'}, status=status.HTTP_400_BAD_REQUEST)
    
    worker_profile = request.user.worker_profile
    if not worker_profile.location_sharing_enabled or not worker_profile.current_latitude:
        return Response({'error': 'الموقع غير متاح','message': 'يجب تفعيل مشاركة الموقع وتحديث موقعك الحالي'}, status=status.HTTP_400_BAD_REQUEST)
    
    distance_max = float(request.query_params.get('distance_max', 30))
    
    tasks_queryset = ServiceRequest.objects.filter(status='published').select_related('client', 'service_category')
    tasks_with_location = tasks_queryset.filter(latitude__isnull=False, longitude__isnull=False)
    
    nearby_tasks = []
    worker_lat = float(worker_profile.current_latitude)
    worker_lng = float(worker_profile.current_longitude)
    
    for task in tasks_with_location:
        distance = worker_profile.calculate_distance_to(float(task.latitude), float(task.longitude))
        if distance and distance <= distance_max:
            task.calculated_distance = distance
            nearby_tasks.append(task)
    
    nearby_tasks.sort(key=lambda x: x.calculated_distance)
    
    from django.core.paginator import Paginator
    paginator = Paginator(nearby_tasks, 20)
    page_number = request.query_params.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = AvailableTaskSerializer(page_obj.object_list, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'message': f'تم العثور على {len(nearby_tasks)} مهمة قريبة',
        'data': {
            'worker_location': {'latitude': worker_lat, 'longitude': worker_lng, 'last_updated': worker_profile.location_last_updated},
            'filter_applied': {'max_distance_km': distance_max, 'total_tasks_found': len(nearby_tasks)},
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': len(nearby_tasks),
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            },
            'tasks': serializer.data
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nearby_workers(request):
    if request.user.role != 'client':
        raise PermissionDenied("هذه الخدمة متاحة للعملاء فقط")
    
    client_lat = request.query_params.get('lat')
    client_lng = request.query_params.get('lng')
    
    if not (client_lat and client_lng):
        return Response({'error': 'إحداثيات مطلوبة','message': 'يجب تقديم lat و lng لموقع العميل'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        client_lat = float(client_lat)
        client_lng = float(client_lng)
    except (ValueError, TypeError):
        return Response({'error': 'إحداثيات غير صحيحة','message': 'lat و lng يجب أن تكون أرقام صحيحة'}, status=status.HTTP_400_BAD_REQUEST)
    
    distance_max = float(request.query_params.get('distance_max', 30))
    category = request.query_params.get('category')
    min_rating = request.query_params.get('min_rating')
    
    workers_queryset = User.objects.filter(
        role='worker',
        is_verified=True,
        onboarding_completed=True,
        worker_profile__is_available=True,
        worker_profile__location_sharing_enabled=True,
        worker_profile__location_status='active',
        worker_profile__current_latitude__isnull=False,
        worker_profile__current_longitude__isnull=False
    ).select_related('worker_profile').prefetch_related('worker_services__category')
    
    if category:
        workers_queryset = workers_queryset.filter(worker_services__category__name__icontains=category)
    
    if min_rating:
        try:
            min_rating_float = float(min_rating)
            workers_queryset = workers_queryset.filter(worker_profile__average_rating__gte=min_rating_float)
        except (ValueError, TypeError):
            pass
    
    nearby_workers = []
    for worker in workers_queryset:
        distance = worker.worker_profile.calculate_distance_to(client_lat, client_lng)
        if distance and distance <= distance_max:
            worker.calculated_distance = distance
            nearby_workers.append(worker)
    
    nearby_workers.sort(key=lambda x: x.calculated_distance)
    
    from django.core.paginator import Paginator
    paginator = Paginator(nearby_workers, 20)
    page_number = request.query_params.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = WorkerProfileListSerializer(page_obj.object_list, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'message': f'تم العثور على {len(nearby_workers)} عامل قريب',
        'data': {
            'client_location': {'latitude': client_lat, 'longitude': client_lng},
            'filter_applied': {'max_distance_km': distance_max,'category_filter': category,'min_rating_filter': min_rating,'total_workers_found': len(nearby_workers)},
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': len(nearby_workers),
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            },
            'workers': serializer.data
        }
    }, status=status.HTTP_200_OK)
