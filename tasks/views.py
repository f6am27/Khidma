#tasks/views.py
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
from rest_framework.permissions import IsAuthenticated

from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification
from notifications.utils import notify_new_task_available, notify_task_published
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
    ✅ مع دعم service_category الاختياري
    """
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        if self.request.user.role != 'client':
            raise PermissionDenied("Only clients can create service requests")
        
        service_request = serializer.save()
        
        # ✅ حفظ الموقع تلقائياً إذا كان GPS
        if service_request.latitude and service_request.longitude:
            from users.models import SavedLocation
            from django.utils import timezone
            
            # تقريب الإحداثيات
            lat_rounded = round(float(service_request.latitude), 5)
            lng_rounded = round(float(service_request.longitude), 5)
            
            # تحقق من وجود الموقع أو أنشئه
            saved_location, created = SavedLocation.objects.get_or_create(
                user=self.request.user,
                latitude=lat_rounded,
                longitude=lng_rounded,
                defaults={
                    'address': service_request.location or 'موقع GPS',
                    'usage_count': 1,
                }
            )
            
            if not created:
                # الموقع موجود → زيادة العداد
                saved_location.usage_count += 1
                saved_location.last_used_at = timezone.now()
                saved_location.save(update_fields=['usage_count', 'last_used_at'])
        
        # ✅ تحذير إذا لم يتم تحديد تصنيف
        warning_message = None
        if not service_request.service_category:
            warning_message = "⚠️ Votre tâche a été publiée sans catégorie. Cela peut réduire le nombre de candidatures."
        
        # ✅ إشعار العميل بنشر المهمة بنجاح
        from notifications.utils import notify_task_published
        notify_task_published(client_user=self.request.user, task=service_request)
        
        # ✅ إعادة response مع تحذير إن وجد
        if warning_message:
            return Response({
                'message': warning_message,
                'task': ServiceRequestDetailSerializer(service_request, context={'request': self.request}).data
            }, status=status.HTTP_201_CREATED)
        
        return service_request

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
        
        if user.role == 'client':
            return ServiceRequest.objects.filter(
                client=user
            ).select_related('service_category', 'assigned_worker')
        
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
        
        # ✅ فلترة التصنيف (مع السماح بـ "Non classifié")
        category = self.request.query_params.get('category')
        if category and category not in ['Tous', 'All', 'Non classifié']:
            queryset = queryset.filter(service_category__name__icontains=category)
        elif category == 'Non classifié':
            queryset = queryset.filter(service_category__isnull=True)
        
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
        
        # ✅ إذا لم يرسل الفرونت الموقع، جرب جلبه من آخر موقع محفوظ
        if not worker_lat or not worker_lng:
            try:
                worker_profile = request.user.worker_profile
                if worker_profile.current_latitude and worker_profile.current_longitude:
                    worker_lat = float(worker_profile.current_latitude)
                    worker_lng = float(worker_profile.current_longitude)
            except:
                pass
        
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
                        task.calculated_distance = distance
                    else:
                        task.calculated_distance = None  # ✅ للمهام بدون موقع
                    
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
        
        # ✅ إذا لم يكن هناك موقع نهائياً، عرض حسب التاريخ
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
    """
    ✅ التقديم على مهمة - مع Soft Lock للعامل
    POST /api/tasks/{task_id}/apply/
    """
    serializer_class = TaskApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # ================================
        # 1️⃣ التحقق من أن المستخدم عامل
        # ================================
        if request.user.role != 'worker':
            raise PermissionDenied("Only workers can apply for tasks")
        
        # ================================
        # 2️⃣ جلب المهمة
        # ================================
        service_request_id = kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='published'
        )
        
        # ================================
        # 3️⃣ التحقق من عدم التقديم مسبقاً
        # ================================
        if TaskApplication.objects.filter(
            service_request=service_request,
            worker=request.user,
            is_active=True
        ).exists():
            return Response({
                'ok': False,
                'error': "Vous avez déjà postulé pour cette mission",
                'error_type': 'already_applied'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ================================
        # 🔒 4️⃣ التحقق من Soft Lock - العامل
        # ================================
        from payments.models import UserTaskCounter
        
        worker_counter, _ = UserTaskCounter.objects.get_or_create(user=request.user)
        
        if worker_counter.needs_payment:  # ✅ صحيح
            from payments.serializers import UserTaskCounterSerializer
            
            return Response({
                'ok': False,
                'subscriptionRequired': True,
                'errorType': 'worker_limit_reached',
                'message': f'Limite atteinte ({worker_counter.current_usage}/{worker_counter.current_limit}). Abonnement requis.',
                'counter': UserTaskCounterSerializer(worker_counter).data,
            }, status=status.HTTP_403_FORBIDDEN)
                
        # ================================
        # 5️⃣ التحقق من التصنيف (إذا موجود)
        # ================================
        if service_request.service_category:
            worker_category = request.user.worker_profile.service_category
            task_category = service_request.service_category

            if hasattr(worker_category, 'id') and hasattr(task_category, 'id'):
                if worker_category.id != task_category.id:
                    return Response({
                        'ok': False,
                        'error': "Vous ne proposez pas ce type de service",
                        'error_type': 'category_mismatch'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                if str(worker_category) != str(task_category):
                    return Response({
                        'ok': False,
                        'error': "Vous ne proposez pas ce type de service",
                        'error_type': 'category_mismatch'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # ================================
        # 6️⃣ إنشاء التطبيق
        # ================================
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application = serializer.save(
            service_request=service_request,
            worker=request.user
        )
        
        # ================================
        # 7️⃣ إشعار العميل
        # ================================
        from notifications.utils import notify_worker_applied
        notify_worker_applied(
            client_user=service_request.client,
            worker_user=request.user,
            task=service_request,
            application=application
        )
        
        # ================================
        # 8️⃣ إرجاع النتيجة
        # ================================
        return Response({
            'ok': True,
            'message': 'Candidature envoyée avec succès',
            'application': TaskApplicationSerializer(application).data
        }, status=status.HTTP_201_CREATED)

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
    """
    ✅ قبول عامل - هنا ينتهي دور التطبيق!
    المهمة تصبح 'active' ويتواصل الطرفان خارج التطبيق
    
    التحديث: Signal يزيد العداد تلقائياً عند حفظ المهمة
    النظام الجديد: دعم المهام المجانية + حزم المهام المدفوعة
    """
    service_request = get_object_or_404(ServiceRequest, id=pk)
    
    # ================================
    # 1️⃣ التحقق من صلاحيات العميل
    # ================================
    if service_request.client != request.user:
        raise PermissionDenied("You can only accept workers for your own tasks")
    
    if service_request.status != 'published':
        raise ValidationError("Task is no longer available for acceptance")
    
    # ================================
    # 2️⃣ الحصول على معرف العامل
    # ================================
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
    
    # ================================
    # 3️⃣ التحقق من حد العميل - النظام الجديد
    # ================================
    from payments.models import UserTaskCounter
    
    client_counter, _ = UserTaskCounter.objects.get_or_create(user=request.user)
    
    if client_counter.needs_payment:
        return Response({
            'error': 'subscription_required',
            'error_type': 'client_limit_reached',
            'message': 'يجب شراء حزمة جديدة للمتابعة (8 مهام بـ 5 أوقيات).',
            'message_fr': 'Achat de bundle requis pour continuer (8 tâches pour 5 MRU).',
            'counter_info': {
                'current_usage': client_counter.current_usage,
                'current_limit': client_counter.current_limit,
                'tasks_remaining': client_counter.tasks_remaining,
                'total_subscriptions': client_counter.total_subscriptions,
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    # ================================
    # 4️⃣ التحقق من حد العامل - النظام الجديد
    # ================================
    worker = application.worker
    worker_counter, _ = UserTaskCounter.objects.get_or_create(user=worker)
    
    if worker_counter.needs_payment:
        return Response({
            'error': 'subscription_required',
            'error_type': 'worker_limit_reached',
            'message': f'العامل {worker.get_full_name() or worker.phone} يحتاج لشراء حزمة جديدة.',
            'message_fr': f'Le travailleur {worker.get_full_name() or worker.phone} doit acheter un nouveau bundle.',
            'worker_info': {
                'name': worker.get_full_name() or worker.phone,
                'current_usage': worker_counter.current_usage,
                'current_limit': worker_counter.current_limit,
                'tasks_remaining': worker_counter.tasks_remaining,
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    # ================================
    # 5️⃣ تحديث حالة الطلب
    # ================================
    application.application_status = 'accepted'
    application.responded_at = timezone.now()
    application.save()
    
    # ================================
    # 6️⃣ تحديث المهمة - Signal يزيد العداد تلقائياً!
    # ================================
    service_request.assigned_worker = application.worker
    service_request.status = 'active'
    service_request.accepted_at = timezone.now()
    service_request.save()  # ✅ Signal يشتغل هنا ويزيد العداد!
    
    # ================================
    # 7️⃣ رفض باقي المتقدمين
    # ================================
    TaskApplication.objects.filter(
        service_request=service_request,
        is_active=True
    ).exclude(id=application.id).update(
        application_status='rejected',
        responded_at=timezone.now()
    )
    
    # ================================
    # 8️⃣ إشعار العامل المقبول
    # ================================
    from notifications.utils import notify_application_accepted
    notify_application_accepted(
        worker_user=application.worker,
        task=service_request,
        client_user=request.user
    )
    
    # ================================
    # 9️⃣ إشعار العمال المرفوضين
    # ================================
    from notifications.utils import notify_application_rejected
    rejected_applications = TaskApplication.objects.filter(
        service_request=service_request,
        application_status='rejected'
    )
    
    for rejected_app in rejected_applications:
        notify_application_rejected(
            worker_user=rejected_app.worker,
            task=service_request
        )
    
    # ================================
    # 🔟 تحديث البيانات بعد Signal
    # ================================
    # Signal قد زاد العداد، نحدث البيانات للحصول على القيم الجديدة
    client_counter.refresh_from_db()
    worker_counter.refresh_from_db()
    
    # ================================
    # 1️⃣1️⃣ إرجاع Response - النظام الجديد
    # ================================
    return Response({
        'ok': True,
        'message': '✅ Worker accepted successfully. The task is now active.',
        'message_fr': '✅ Travailleur accepté avec succès. La tâche est maintenant active.',
        'task_status': 'active',
        'assigned_worker': application.worker.get_full_name() or application.worker.phone,
        'note': 'Le travail sera effectué en dehors de l\'application. Vous pouvez contacter le travailleur directement.',
        
        # ✅ معلومات العداد المحدثة (بعد Signal)
        'task_counter': {
            'client': {
                'current_usage': client_counter.current_usage,
                'current_limit': client_counter.current_limit,
                'tasks_remaining': client_counter.tasks_remaining,
                'needs_payment': client_counter.needs_payment,
                'total_subscriptions': client_counter.total_subscriptions,
            },
            'worker': {
                'current_usage': worker_counter.current_usage,
                'current_limit': worker_counter.current_limit,
                'tasks_remaining': worker_counter.tasks_remaining,
                'needs_payment': worker_counter.needs_payment,
                'total_subscriptions': worker_counter.total_subscriptions,
            }
        }
    })
@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_task_status(request, pk):
    """
    ✅ تحديث حالة المهمة - الآن فقط: cancelled
    ❌ حذف: start_work, work_completed, completed
    """
    service_request = get_object_or_404(ServiceRequest, id=pk)
    new_status = request.data.get('status')
    
    if not new_status:
        raise ValidationError("Status is required")
    
    # ✅ الحالة الوحيدة المسموحة: cancelled
    if new_status == 'cancelled':
        if service_request.client != request.user:
            raise PermissionDenied("You can only cancel your own tasks")
        if service_request.status not in ['published', 'active']:
            raise ValidationError("Only published or active tasks can be cancelled")
        
        service_request.status = 'cancelled'
        service_request.cancelled_at = timezone.now()
        service_request.save()
        
        # ✅ إشعار العامل بالإلغاء (إن وجد)
        if service_request.assigned_worker:
            from notifications.utils import notify_service_cancelled
            notify_service_cancelled(
                client_user=request.user,
                worker_user=service_request.assigned_worker,
                task=service_request,
                reason=""
            )
        
        return Response({
            'message': 'Task cancelled successfully',
            'task_status': 'cancelled'
        })
    
    else:
        # ❌ أي حالة أخرى غير مسموحة
        raise ValidationError(
            "Invalid status. Only 'cancelled' is allowed. "
            "Work happens outside the app after worker acceptance."
        )


class TaskReviewCreateView(generics.CreateAPIView):
    """
    ✅ التقييم يبقى - العميل يمكنه تقييم العامل بعد انتهاء العمل خارج التطبيق
    """
    serializer_class = TaskReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        service_request_id = self.kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='active'  # ✅ يمكن التقييم على المهام النشطة
        )
        
        if service_request.client != self.request.user:
            raise PermissionDenied("You can only review your own tasks")
        
        if hasattr(service_request, 'review'):
            raise ValidationError("Task already reviewed")
        
        if not service_request.assigned_worker:
            raise ValidationError("Cannot review a task without an assigned worker")
        
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
    """
    ✅ إحصائيات المهام - محدثة للنظام الجديد
    """
    user = request.user
    if user.role == 'client':
        stats = {
            'published': ServiceRequest.objects.filter(client=user, status='published').count(),
            'active': ServiceRequest.objects.filter(client=user, status='active').count(),
            'cancelled': ServiceRequest.objects.filter(client=user, status='cancelled').count(),
            'total_tasks': ServiceRequest.objects.filter(client=user).count(),
            # ❌ حذف: completed, total_spent
        }
    elif user.role == 'worker':
        stats = {
            'applications_sent': TaskApplication.objects.filter(worker=user).count(),
            'applications_pending': TaskApplication.objects.filter(worker=user, application_status='pending').count(),
            'applications_accepted': TaskApplication.objects.filter(worker=user, application_status='accepted').count(),
            'tasks_active': ServiceRequest.objects.filter(assigned_worker=user, status='active').count(),
            'total_applications': TaskApplication.objects.filter(worker=user).count(),
            # ❌ حذف: tasks_completed, total_earned
        }
    else:
        stats = {
            'total_tasks': ServiceRequest.objects.count(),
            'published_tasks': ServiceRequest.objects.filter(status='published').count(),
            'active_tasks': ServiceRequest.objects.filter(status='active').count(),
            'cancelled_tasks': ServiceRequest.objects.filter(status='cancelled').count(),
            'total_applications': TaskApplication.objects.count(),
            'total_reviews': TaskReview.objects.count(),
            'average_rating': TaskReview.objects.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
        }
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tasks_map_data(request):
    """
    API مخصص لعرض المهام على الخريطة التفاعلية للعامل
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
    
    if not worker_profile.location_sharing_enabled or not worker_profile.current_latitude:
        return Response({
            'error': 'مشاركة الموقع غير مفعلة',
            'message': 'يجب تفعيل مشاركة الموقع لعرض الخريطة',
            'worker_location': None,
            'tasks': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    distance_max = float(request.query_params.get('distance_max', 30))
    category = request.query_params.get('category')
    min_budget = request.query_params.get('min_budget')
    max_budget = request.query_params.get('max_budget')
    urgent_only = request.query_params.get('urgent_only', 'false').lower() == 'true'
    
    queryset = ServiceRequest.objects.filter(
        status='published',
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('client', 'service_category')
    
    # ✅ فلترة التصنيف (مع السماح بـ null)
    if category and category != 'Non classifié':
        queryset = queryset.filter(service_category__name__icontains=category)
    elif category == 'Non classifié':
        queryset = queryset.filter(service_category__isnull=True)
    
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
    
    nearby_tasks.sort(key=lambda x: x.calculated_distance)
    
    max_tasks = int(request.query_params.get('max_tasks', 50))
    nearby_tasks = nearby_tasks[:max_tasks]
    
    serializer = TaskMapDataSerializer(nearby_tasks, many=True, context={'request': request})
    
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


# ✅ نبقي APIs التقييمات كما هي
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
    
    search_fields = ['review_text', 'service_request__title']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role != 'worker':
            return TaskReview.objects.none()
        
        queryset = TaskReview.objects.filter(
            service_request__assigned_worker=user
        ).select_related(
            'service_request',
            'service_request__client',
            'service_request__assigned_worker',
            'service_request__service_category'
        ).order_by('-created_at')
        
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
        queryset = self.get_queryset()
        
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        total_count = queryset.count()
        
        stats = queryset.aggregate(
            average_rating=Avg('rating'),
            total_reviews=Count('id'),
            five_stars=Count('id', filter=Q(rating=5)),
            four_stars=Count('id', filter=Q(rating=4)),
            three_stars=Count('id', filter=Q(rating=3)),
            two_stars=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )
        
        paginated_queryset = queryset[offset:offset + limit]
        
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_worker_applications_stats(request):
    """
    Get worker's applications statistics
    """
    worker = request.user
    
    pending = TaskApplication.objects.filter(
        worker=worker,
        application_status='pending'
    ).count()
    
    accepted = TaskApplication.objects.filter(
        worker=worker,
        application_status='accepted'
    ).count()
    
    rejected = TaskApplication.objects.filter(
        worker=worker,
        application_status='rejected'
    ).count()
    
    return Response({
        'pending': pending,
        'accepted': accepted,
        'rejected': rejected,
        'total': pending + accepted + rejected
    })