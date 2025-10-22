# tasks/views.py
from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404
import random
from math import radians, cos, sin, asin, sqrt

from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification
from .serializers import (
    ServiceRequestListSerializer,
    ServiceRequestDetailSerializer, 
    ServiceRequestCreateSerializer,
    AvailableTaskSerializer,
    TaskApplicationSerializer,
    TaskApplicationCreateSerializer,
    TaskReviewSerializer,
    TaskNotificationSerializer,
    TaskMapDataSerializer
)
from users.models import User
from services.models import ServiceCategory

class ServiceRequestCreateView(generics.CreateAPIView):
    """
    Create new service request (for clients)
    إنشاء طلب خدمة جديد (للعملاء)
    """
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        if self.request.user.role != 'client':
            raise PermissionDenied("Only clients can create service requests")
        service_request = serializer.save()
        self._notify_workers(service_request)
        return service_request
    
    def _notify_workers(self, service_request):
        """Notify workers in the same category and area"""
        relevant_workers = User.objects.filter(
            worker_services__category=service_request.service_category,
            worker_profile__is_available=True,
            onboarding_completed=True,
            worker_profile__service_area__icontains=service_request.location.split(',')[0]
        ).distinct()
        for worker in relevant_workers[:10]:
            TaskNotification.objects.create(
                recipient=worker,
                service_request=service_request,
                notification_type='task_posted',
                title=f'Nouvelle tâche disponible: {service_request.service_category.name}',
                message=f'Une nouvelle tâche "{service_request.title}" est disponible dans votre zone.'
            )


class ClientTasksListView(generics.ListAPIView):
    """
    Get my tasks - works for both client and worker
    للعميل: يعيد المهام التي أنشأها
    للعامل: يعيد المهام المقبولة له
    """
    serializer_class = ServiceRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        user = self.request.user
        
        # Client: return tasks created by them
        if user.role == 'client':
            return ServiceRequest.objects.filter(
                client=user
            ).select_related('service_category', 'assigned_worker')
        
        # Worker: return tasks assigned to them
        elif user.role == 'worker':
            return ServiceRequest.objects.filter(
                assigned_worker=user
            ).select_related('service_category', 'client')
        
        return ServiceRequest.objects.none()

class ServiceRequestDetailView(generics.RetrieveAPIView):
    serializer_class = ServiceRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'client':
            return ServiceRequest.objects.filter(client=user)
        elif user.role == 'worker':
            return ServiceRequest.objects.filter(
                Q(status='published') |
                Q(assigned_worker=user)
            )
        return ServiceRequest.objects.none()


class ServiceRequestUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ServiceRequest.objects.filter(
            client=self.request.user,
            status='published'
        )
    
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        task = serializer.save()
        if task.applications.filter(is_active=True).exists():
            for application in task.applications.filter(is_active=True):
                TaskNotification.objects.create(
                    recipient=application.worker,
                    service_request=task,
                    notification_type='task_updated',
                    title='Tâche mise à jour',
                    message=f'La tâche "{task.title}" a été mise à jour.'
                )



class AvailableTasksListView(generics.ListAPIView):
    serializer_class = AvailableTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        if self.request.user.role != 'worker':
            return ServiceRequest.objects.none()
        
        queryset = ServiceRequest.objects.filter(
            status='published'
        ).select_related('client', 'service_category')
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(service_category__name__icontains=category)
        
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        budget_min = self.request.query_params.get('budget_min')
        if budget_min:
            queryset = queryset.filter(budget__gte=budget_min)
        
        budget_max = self.request.query_params.get('budget_max')
        if budget_max:
            queryset = queryset.filter(budget__lte=budget_max)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        worker_lat = request.query_params.get('lat')
        worker_lng = request.query_params.get('lng')
        sort_by = request.query_params.get('sort_by', 'latest')
        limit = request.query_params.get('limit')
        
        if worker_lat and worker_lng:
            try:
                worker_lat = float(worker_lat)
                worker_lng = float(worker_lng)
                
                tasks_with_distance = []
                for task in queryset:
                    if task.latitude and task.longitude:
                        distance = self._calculate_distance(
                            worker_lat, worker_lng,
                            float(task.latitude), float(task.longitude)
                        )
                    else:
                        distance = None
                    
                    task.calculated_distance = distance
                    tasks_with_distance.append(task)
                
                if sort_by == 'nearest':
                    tasks_with_distance.sort(
                        key=lambda x: x.calculated_distance if x.calculated_distance is not None else 999999
                    )
                elif sort_by == 'budget_low':
                    tasks_with_distance.sort(key=lambda x: x.budget)
                elif sort_by == 'budget_high':
                    tasks_with_distance.sort(key=lambda x: -x.budget)
                elif sort_by == 'urgent':
                    tasks_with_distance.sort(key=lambda x: (-x.is_urgent, -x.created_at.timestamp()))
                else:
                    tasks_with_distance.sort(key=lambda x: -x.created_at.timestamp())
                
                if limit:
                    tasks_with_distance = tasks_with_distance[:int(limit)]
                
                serializer = self.get_serializer(tasks_with_distance, many=True)
                return Response({
                    'count': len(tasks_with_distance),
                    'results': serializer.data
                })
                
            except (ValueError, TypeError) as e:
                return Response({'error': f'Invalid coordinates: {str(e)}'}, status=400)
        
        if sort_by == 'budget_high':
            queryset = queryset.order_by('-budget')
        elif sort_by == 'budget_low':
            queryset = queryset.order_by('budget')
        elif sort_by == 'urgent':
            queryset = queryset.order_by('-is_urgent', '-created_at')
        else:
            queryset = queryset.order_by('-created_at')
        
        if limit:
            queryset = queryset[:int(limit)]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count() if hasattr(queryset, 'count') else len(queryset),
            'results': serializer.data
        })
    
    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return round(c * r, 2)
    
class TaskApplicationCreateView(generics.CreateAPIView):
    serializer_class = TaskApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        if request.user.role != 'worker':
            raise PermissionDenied("Only workers can apply for tasks")
        
        service_request_id = kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='published'
        )
        
        if TaskApplication.objects.filter(
            service_request=service_request,
            worker=request.user,
            is_active=True
        ).exists():
            raise ValidationError("You have already applied for this task")
        
        # ✅ معالجة آمنة تتعامل مع كل الحالات
        worker_category = request.user.worker_profile.service_category
        task_category = service_request.service_category

        # التحقق: إذا كانا objects، قارن بـ id
        # إذا كانا strings، قارن مباشرة
        if hasattr(worker_category, 'id') and hasattr(task_category, 'id'):
            # حالة: Foreign Key Objects
            if worker_category.id != task_category.id:
                raise ValidationError("You don't offer this type of service")
        else:
            # حالة: String values
            if str(worker_category) != str(task_category):
                raise ValidationError("You don't offer this type of service")
                
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application = serializer.save(
            service_request=service_request,
            worker=request.user
        )
        
        TaskNotification.objects.create(
            recipient=service_request.client,
            service_request=service_request,
            task_application=application,
            notification_type='application_received',
            title='Nouvelle candidature reçue',
            message=f'{request.user.get_full_name() or request.user.phone} s\'est porté candidat pour "{service_request.title}"'
        )
        
        return Response(
            TaskApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED
        )


class TaskCandidatesListView(generics.ListAPIView):
    serializer_class = TaskApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        service_request_id = self.kwargs.get('pk')
        service_request = get_object_or_404(ServiceRequest, id=service_request_id)
        
        if service_request.client != self.request.user:
            raise PermissionDenied("You can only view candidates for your own tasks")
        
        return TaskApplication.objects.filter(
            service_request=service_request,
            is_active=True
        ).select_related('worker').order_by('-applied_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_worker(request, pk):
    service_request = get_object_or_404(ServiceRequest, id=pk)
    
    if service_request.client != request.user:
        raise PermissionDenied("You can only accept workers for your own tasks")
    
    if service_request.status != 'published':
        raise ValidationError("Task is no longer available for acceptance")
    
    worker_id = request.data.get('worker_id')
    if not worker_id:
        raise ValidationError("Worker ID is required")
    
    application = get_object_or_404(
        TaskApplication,
        service_request=service_request,
        worker_id=worker_id,
        is_active=True,
        application_status='pending'
    )
    
    application.application_status = 'accepted'
    application.responded_at = timezone.now()
    application.save()
    
    service_request.assigned_worker = application.worker
    service_request.status = 'active'
    service_request.accepted_at = timezone.now()
    service_request.save()
    
    TaskApplication.objects.filter(
        service_request=service_request,
        is_active=True
    ).exclude(id=application.id).update(
        application_status='rejected',
        responded_at=timezone.now()
    )
    
    TaskNotification.objects.create(
        recipient=application.worker,
        service_request=service_request,
        task_application=application,
        notification_type='application_accepted',
        title='Candidature acceptée!',
        message=f'Votre candidature pour "{service_request.title}" a été acceptée!'
    )
    
    rejected_applications = TaskApplication.objects.filter(
        service_request=service_request,
        application_status='rejected'
    )
    
    for rejected_app in rejected_applications:
        TaskNotification.objects.create(
            recipient=rejected_app.worker,
            service_request=service_request,
            task_application=rejected_app,
            notification_type='application_rejected',
            title='Candidature non retenue',
            message=f'Votre candidature pour "{service_request.title}" n\'a pas été retenue cette fois.'
        )
    
    return Response({
        'message': 'Worker accepted successfully',
        'task_status': 'active',
        'assigned_worker': application.worker.get_full_name() or application.worker.phone
    })


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_task_status(request, pk):
    service_request = get_object_or_404(ServiceRequest, id=pk)
    new_status = request.data.get('status')
    
    if not new_status:
        raise ValidationError("Status is required")
    
    if new_status == 'start_work':
        if request.user.role != 'worker':
            raise PermissionDenied("Only workers can start work")
        if service_request.assigned_worker != request.user:
            raise PermissionDenied("Only the assigned worker can start this work")
        if service_request.status != 'active':
            raise ValidationError("Task must be active to start work")
        
        service_request.work_started_at = timezone.now()
        service_request.save()
        
        TaskNotification.objects.create(
            recipient=service_request.client,
            service_request=service_request,
            notification_type='work_started',
            title='Work started',
            message=f'Worker has started work on "{service_request.title}".'
        )
        return Response({'message': 'Work started successfully.'})
    
    if new_status == 'work_completed':
        if request.user.role != 'worker':
            raise PermissionDenied("Only workers can mark work as completed")
        if service_request.assigned_worker != request.user:
            raise PermissionDenied("Only the assigned worker can mark this work as completed")
        if service_request.status != 'active':
            raise ValidationError("Task must be active to mark as work completed")
        
        service_request.status = 'work_completed'
        service_request.work_completed_at = timezone.now()
        service_request.save()
        
        TaskNotification.objects.create(
            recipient=service_request.client,
            service_request=service_request,
            notification_type='work_completed',
            title='Work completed',
            message=f'Worker has completed work on "{service_request.title}". Please verify and confirm.'
        )
        return Response({'message': 'Work marked as completed. Waiting for client confirmation.'})
    
    elif new_status == 'completed':
        if service_request.client != request.user:
            raise PermissionDenied("Only the client can confirm task completion")
        if service_request.status != 'work_completed':
            raise ValidationError("Work must be marked as completed by worker first")
        
        # Get final_price from request
        final_price = request.data.get('final_price')
        
        print(f'════════ PAYMENT DEBUG ════════')
        print(f'Task ID: {service_request.id}')
        print(f'Received final_price: {final_price}')
        print(f'Type: {type(final_price)}')
        print(f'Budget: {service_request.budget}')
        print(f'═══════════════════════════════')
        
        # Validate final_price
        if final_price is None or final_price == '':
            raise ValidationError({
                'final_price': 'Final price is required'
            })
        
        # Convert to float safely
        try:
            final_price_float = float(final_price)
            
            if final_price_float <= 0:
                raise ValidationError({
                    'final_price': 'Amount must be greater than zero'
                })
            
            service_request.final_price = final_price_float
            
        except (ValueError, TypeError) as e:
            raise ValidationError({
                'final_price': f'Invalid amount format: {str(e)}'
            })
        
        # Update task status
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()
        
        print(f'✅ Task saved with final_price: {service_request.final_price}')
        
        # ✅ CREATE PAYMENT AUTOMATICALLY
        from payments.models import Payment
        
        payment = Payment.objects.create(
            task=service_request,
            payer=service_request.client,
            receiver=service_request.assigned_worker,
            amount=final_price_float,
            payment_method='cash',
            status='completed'
        )
        
        print(f'✅ Payment created: {payment.id} - Amount: {payment.amount} MRU')
        
        # Update worker stats
        worker = service_request.assigned_worker
        if hasattr(worker, 'worker_profile'):
            worker.worker_profile.total_jobs_completed += 1
            worker.worker_profile.save()
        
        # Send notification to worker
        TaskNotification.objects.create(
            recipient=worker,
            service_request=service_request,
            notification_type='task_completed',
            title='Task completed and paid',
            message=f'Task "{service_request.title}" completed and paid. Amount: {service_request.final_price} MRU'
        )
        
        return Response({
            'message': 'Task completed and payment recorded successfully',
            'final_price': float(service_request.final_price),
            'payment_id': payment.id,
            'task_id': service_request.id
        })
    
    elif new_status == 'cancelled':
        if service_request.client != request.user:
            raise PermissionDenied("You can only cancel your own tasks")
        if service_request.status not in ['published', 'active']:
            raise ValidationError("Only published or active tasks can be cancelled")
        
        service_request.status = 'cancelled'
        service_request.cancelled_at = timezone.now()
        service_request.save()
        
        if service_request.assigned_worker:
            TaskNotification.objects.create(
                recipient=service_request.assigned_worker,
                service_request=service_request,
                notification_type='task_cancelled',
                title='Task cancelled',
                message=f'Task "{service_request.title}" has been cancelled by the client.'
            )
        
        return Response({'message': 'Task cancelled successfully'})
    
    else:
        raise ValidationError("Invalid status")
    

class TaskReviewCreateView(generics.CreateAPIView):
    serializer_class = TaskReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        service_request_id = self.kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='completed'
        )
        
        if service_request.client != self.request.user:
            raise PermissionDenied("You can only review your own completed tasks")
        
        if hasattr(service_request, 'review'):
            raise ValidationError("Task already reviewed")
        
        review = serializer.save(
            service_request=service_request,
            client=self.request.user,
            worker=service_request.assigned_worker
        )
        
        TaskNotification.objects.create(
            recipient=service_request.assigned_worker,
            service_request=service_request,
            notification_type='review_received',
            title='Nouvelle évaluation reçue',
            message=f'Vous avez reçu une évaluation de {review.rating} étoiles pour "{service_request.title}"'
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_stats(request):
    user = request.user
    if user.role == 'client':
        stats = {
            'published': ServiceRequest.objects.filter(client=user, status='published').count(),
            'active': ServiceRequest.objects.filter(client=user, status='active').count(),
            'completed': ServiceRequest.objects.filter(client=user, status='completed').count(),
            'cancelled': ServiceRequest.objects.filter(client=user, status='cancelled').count(),
            'total_spent': 0,
        }
    elif user.role == 'worker':
        stats = {
            'applications_sent': TaskApplication.objects.filter(worker=user).count(),
            'applications_pending': TaskApplication.objects.filter(worker=user, application_status='pending').count(),
            'applications_accepted': TaskApplication.objects.filter(worker=user, application_status='accepted').count(),
            'tasks_active': ServiceRequest.objects.filter(assigned_worker=user, status='active').count(),
            'tasks_completed': ServiceRequest.objects.filter(assigned_worker=user, status='completed').count(),
            'total_earned': 0,
        }
    else:
        stats = {
            'total_tasks': ServiceRequest.objects.count(),
            'published_tasks': ServiceRequest.objects.filter(status='published').count(),
            'active_tasks': ServiceRequest.objects.filter(status='active').count(),
            'completed_tasks': ServiceRequest.objects.filter(status='completed').count(),
            'cancelled_tasks': ServiceRequest.objects.filter(status='cancelled').count(),
            'total_applications': TaskApplication.objects.count(),
            'total_reviews': TaskReview.objects.count(),
            'average_rating': TaskReview.objects.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
        }
    return Response(stats)


# تحديث AvailableTaskSerializer لإظهار المسافة المحسوبة
class AvailableTaskSerializer(serializers.ModelSerializer):
    """
    تحديث: إضافة المسافة المحسوبة من موقع العامل
    """
    distance_from_worker = serializers.SerializerMethodField()
    exact_distance_km = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'category',
            'budget', 'location', 'preferred_time', 'is_urgent',
            'requires_materials', 'createdAt', 'applicantsCount',
            'client_name', 'client_rating', 'distance',
            'has_applied', 'application_status',
            'distance_from_worker', 'exact_distance_km'
        ]
    
    def get_distance_from_worker(self, obj):
        if hasattr(obj, 'calculated_distance'):
            return f"{obj.calculated_distance:.1f} km"
        return self.get_distance(obj)
    
    def get_exact_distance_km(self, obj):
        if hasattr(obj, 'calculated_distance'):
            return round(obj.calculated_distance, 1)
        return None
    
    def get_distance(self, obj):
        if hasattr(obj, 'calculated_distance'):
            return f"{obj.calculated_distance:.1f} km"
        return f"{random.uniform(0.5, 10.0):.1f} km"


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tasks_map_data(request):
    """
    API مخصص لعرض المهام على الخريطة التفاعلية للعامل
    يعيد بيانات مبسطة ومحسنة للخرائط مع موقع العامل
    """
    if request.user.role != 'worker':
        raise PermissionDenied("هذه الخدمة متاحة للعمال فقط")
    
    if not hasattr(request.user, 'worker_profile'):
        return Response({
            'error': 'ملف العامل غير مكتمل',
            'worker_location': None,
            'tasks': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    worker_profile = request.user.worker_profile
    
    # التحقق من تفعيل مشاركة الموقع
    if not worker_profile.location_sharing_enabled or not worker_profile.current_latitude:
        return Response({
            'error': 'مشاركة الموقع غير مفعلة',
            'message': 'يجب تفعيل مشاركة الموقع لعرض الخريطة',
            'worker_location': None,
            'tasks': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # معاملات الفلترة
    distance_max = float(request.query_params.get('distance_max', 30))
    category = request.query_params.get('category')
    min_budget = request.query_params.get('min_budget')
    max_budget = request.query_params.get('max_budget')
    urgent_only = request.query_params.get('urgent_only', 'false').lower() == 'true'
    
    # الحصول على المهام التي لها إحداثيات دقيقة فقط
    queryset = ServiceRequest.objects.filter(
        status='published',
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('client', 'service_category')
    
    # تطبيق الفلاتر
    if category:
        queryset = queryset.filter(service_category__name__icontains=category)
    
    if min_budget:
        try:
            queryset = queryset.filter(budget__gte=float(min_budget))
        except (ValueError, TypeError):
            pass
    
    if max_budget:
        try:
            queryset = queryset.filter(budget__lte=float(max_budget))
        except (ValueError, TypeError):
            pass
    
    if urgent_only:
        queryset = queryset.filter(is_urgent=True)
    
    # فلترة المهام القريبة وحساب المسافة
    worker_lat = float(worker_profile.current_latitude)
    worker_lng = float(worker_profile.current_longitude)
    
    nearby_tasks = []
    for task in queryset:
        distance = worker_profile.calculate_distance_to(
            float(task.latitude), float(task.longitude)
        )
        if distance and distance <= distance_max:
            task.calculated_distance = distance
            nearby_tasks.append(task)
    
    # ترتيب حسب القرب
    nearby_tasks.sort(key=lambda x: x.calculated_distance)
    
    # تحديد العدد الأقصى للمهام المعروضة على الخريطة
    max_tasks = int(request.query_params.get('max_tasks', 50))
    nearby_tasks = nearby_tasks[:max_tasks]
    
    # تحويل البيانات
    serializer = TaskMapDataSerializer(nearby_tasks, many=True, context={'request': request})
    
    # إحصائيات إضافية للخريطة
    stats = {
        'total_found': len(nearby_tasks),
        'urgent_count': sum(1 for task in nearby_tasks if task.is_urgent),
        'avg_distance': round(sum(task.calculated_distance for task in nearby_tasks) / len(nearby_tasks), 1) if nearby_tasks else 0,
        'budget_range': {
            'min': min(float(task.budget) for task in nearby_tasks) if nearby_tasks else 0,
            'max': max(float(task.budget) for task in nearby_tasks) if nearby_tasks else 0
        }
    }
    
    return Response({
        'success': True,
        'worker_location': {
            'latitude': worker_lat,
            'longitude': worker_lng,
            'last_updated': worker_profile.location_last_updated,
            'location_status': worker_profile.location_status,
            'is_fresh': worker_profile.is_location_fresh()
        },
        'filters_applied': {
            'distance_max_km': distance_max,
            'category': category,
            'urgent_only': urgent_only,
            'budget_range': f"{min_budget or 'أي'} - {max_budget or 'أي'}"
        },
        'statistics': stats,
        'tasks': serializer.data
    }, status=status.HTTP_200_OK)

# tasks/views.py
from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from django_filters.rest_framework import DjangoFilterBackend
from .models import TaskReview, ServiceRequest
from .serializers import TaskReviewSerializer


class WorkerReceivedReviewsView(generics.ListAPIView):

    serializer_class = TaskReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Search in review text and task title
    search_fields = ['review_text', 'service_request__title']
    
    # Allow ordering by these fields
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']  # Default: newest first
    
    def get_queryset(self):
        """Get reviews for authenticated worker only"""
        user = self.request.user
        
        # Only workers can view received reviews
        if user.role != 'worker':
            return TaskReview.objects.none()
        
        # Get reviews where user is the assigned worker
        queryset = TaskReview.objects.filter(
            service_request__assigned_worker=user
        ).select_related(
            'service_request',
            'service_request__client',
            'service_request__assigned_worker',
            'service_request__service_category'
        ).order_by('-created_at')
        
        # Filter by rating if provided
        rating = self.request.query_params.get('rating')
        if rating:
            try:
                rating_int = int(rating)
                if 1 <= rating_int <= 5:
                    queryset = queryset.filter(rating=rating_int)
            except ValueError:
                pass
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override to add statistics in response"""
        queryset = self.get_queryset()
        
        # Pagination
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        total_count = queryset.count()
        
        # Calculate statistics
        stats = queryset.aggregate(
            average_rating=Avg('rating'),
            total_reviews=Count('id'),
            five_stars=Count('id', filter=Q(rating=5)),
            four_stars=Count('id', filter=Q(rating=4)),
            three_stars=Count('id', filter=Q(rating=3)),
            two_stars=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )
        
        # Apply pagination
        paginated_queryset = queryset[offset:offset + limit]
        
        # Serialize data
        serializer = self.get_serializer(paginated_queryset, many=True)
        
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'statistics': {
                'average_rating': round(float(stats['average_rating'] or 0), 1),
                'total_reviews': stats['total_reviews'],
                'rating_breakdown': {
                    '5': stats['five_stars'],
                    '4': stats['four_stars'],
                    '3': stats['three_stars'],
                    '2': stats['two_stars'],
                    '1': stats['one_star'],
                }
            },
            'results': serializer.data
        })


class TaskReviewStatsView(generics.GenericAPIView):
    """
    Get review statistics for worker
    GET /tasks/review-stats/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role != 'worker':
            return Response({
                'error': 'Only workers can view review statistics'
            }, status=403)
        
        reviews = TaskReview.objects.filter(
            service_request__assigned_worker=user
        )
        
        stats = reviews.aggregate(
            average_rating=Avg('rating'),
            total_reviews=Count('id'),
            five_stars=Count('id', filter=Q(rating=5)),
            four_stars=Count('id', filter=Q(rating=4)),
            three_stars=Count('id', filter=Q(rating=3)),
            two_stars=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )
        
        return Response({
            'average_rating': round(float(stats['average_rating'] or 0), 1),
            'total_reviews': stats['total_reviews'],
            'rating_breakdown': {
                '5': stats['five_stars'],
                '4': stats['four_stars'],
                '3': stats['three_stars'],
                '2': stats['two_stars'],
                '1': stats['one_star'],
            },
            'rating_percentages': {
                '5': round((stats['five_stars'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0, 1),
                '4': round((stats['four_stars'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0, 1),
                '3': round((stats['three_stars'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0, 1),
                '2': round((stats['two_stars'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0, 1),
                '1': round((stats['one_star'] / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0, 1),
            }
        })