# tasks/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
import random

from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification
from .serializers import (
    ServiceRequestListSerializer,
    ServiceRequestDetailSerializer, 
    ServiceRequestCreateSerializer,
    AvailableTaskSerializer,
    TaskApplicationSerializer,
    TaskApplicationCreateSerializer,
    TaskReviewSerializer,
    TaskNotificationSerializer
)
from workers.models import WorkerProfile
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
        # Ensure user is a client
        if self.request.user.profile.role != 'client':
            raise PermissionDenied("Only clients can create service requests")
        
        # Create the service request
        service_request = serializer.save()
        
        # Send notification to relevant workers (async in production)
        self._notify_workers(service_request)
        
        return service_request
    
    def _notify_workers(self, service_request):
        """Notify workers in the same category and area"""
        # Find workers who can handle this service
        relevant_workers = WorkerProfile.objects.filter(
            services__category=service_request.service_category,
            is_available=True,
            profile__onboarding_completed=True,
            service_area__icontains=service_request.location.split(',')[0]
        ).distinct()
        
        # Create notifications (limit to 10 workers to avoid spam)
        for worker in relevant_workers[:10]:
            TaskNotification.objects.create(
                recipient=worker.profile,
                service_request=service_request,
                notification_type='task_posted',
                title=f'Nouvelle tâche disponible: {service_request.service_category.name}',
                message=f'Une nouvelle tâche "{service_request.title}" est disponible dans votre zone.'
            )


class ClientTasksListView(generics.ListAPIView):
    """
    List client's own tasks by status (Flutter tabs)
    قائمة مهام العميل حسب الحالة (تبويبات Flutter)
    """
    serializer_class = ServiceRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        # Only return client's own tasks
        if self.request.user.profile.role != 'client':
            return ServiceRequest.objects.none()
        
        return ServiceRequest.objects.filter(
            client=self.request.user.profile
        ).select_related('service_category', 'assigned_worker__profile__user')


class ServiceRequestDetailView(generics.RetrieveAPIView):
    """
    Get service request details
    تفاصيل طلب الخدمة
    """
    serializer_class = ServiceRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_profile = self.request.user.profile
        
        if user_profile.role == 'client':
            # Clients can only see their own tasks
            return ServiceRequest.objects.filter(client=user_profile)
        elif user_profile.role == 'worker':
            # Workers can see published tasks and their accepted tasks
            try:
                worker_profile = user_profile.worker_profile
                return ServiceRequest.objects.filter(
                    Q(status='published') |
                    Q(assigned_worker=worker_profile)
                )
            except:
                return ServiceRequest.objects.none()
        
        return ServiceRequest.objects.none()


class ServiceRequestUpdateView(generics.UpdateAPIView):
    """
    Update service request (only for published tasks by client)
    تحديث طلب الخدمة (للمهام المنشورة من قبل العميل فقط)
    """
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only client can update their own published tasks
        return ServiceRequest.objects.filter(
            client=self.request.user.profile,
            status='published'
        )
    
    def update(self, request, *args, **kwargs):
        """Override update method to support partial updates"""
        # Always use partial update (PATCH behavior for PUT)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        task = serializer.save()
        
        # Notify workers about task update only if there are applications
        if task.applications.filter(is_active=True).exists():
            for application in task.applications.filter(is_active=True):
                TaskNotification.objects.create(
                    recipient=application.worker.profile,
                    service_request=task,
                    notification_type='task_updated',
                    title='Tâche mise à jour',
                    message=f'La tâche "{task.title}" a été mise à jour.'
                )

class AvailableTasksListView(generics.ListAPIView):
    """
    List available tasks for workers to apply
    قائمة المهام المتاحة للعمال للتقدم لها
    """
    serializer_class = AvailableTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    
    def get_queryset(self):
        # Only workers can see available tasks
        if self.request.user.profile.role != 'worker':
            return ServiceRequest.objects.none()
        
        try:
            worker_profile = self.request.user.profile.worker_profile
        except:
            return ServiceRequest.objects.none()
        
        # Filter tasks that match worker's skills
        worker_categories = worker_profile.services.values_list('category', flat=True)
        
        queryset = ServiceRequest.objects.filter(
            status='published',
            service_category__in=worker_categories
        ).select_related('client__user', 'service_category')
        
        # Apply filters
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
        
        # Sort options
        sort_by = self.request.query_params.get('sort_by', 'latest')
        if sort_by == 'budget_high':
            queryset = queryset.order_by('-budget')
        elif sort_by == 'budget_low':
            queryset = queryset.order_by('budget')
        elif sort_by == 'urgent':
            queryset = queryset.order_by('-is_urgent', '-created_at')
        else:  # latest
            queryset = queryset.order_by('-created_at')
        
        return queryset


class TaskApplicationCreateView(generics.CreateAPIView):
    """
    Apply for a task (worker applies to service request)
    التقدم للمهمة (العامل يتقدم لطلب الخدمة)
    """
    serializer_class = TaskApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Ensure user is a worker
        if request.user.profile.role != 'worker':
            raise PermissionDenied("Only workers can apply for tasks")
        
        try:
            worker_profile = request.user.profile.worker_profile
        except:
            raise ValidationError("Worker profile not found")
        
        # Get service request
        service_request_id = kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='published'
        )
        
        # Check if worker already applied
        if TaskApplication.objects.filter(
            service_request=service_request,
            worker=worker_profile,
            is_active=True
        ).exists():
            raise ValidationError("You have already applied for this task")
        
        # Check if worker offers this service
        if not worker_profile.services.filter(
            category=service_request.service_category
        ).exists():
            raise ValidationError("You don't offer this type of service")
        
        # Create application with context
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application = serializer.save(
            service_request=service_request,
            worker_profile=worker_profile
        )
        
        # Notify client about new application
        TaskNotification.objects.create(
            recipient=service_request.client,
            service_request=service_request,
            task_application=application,
            notification_type='application_received',
            title='Nouvelle candidature reçue',
            message=f'{worker_profile.user.get_full_name() or worker_profile.user.username} s\'est porté candidat pour "{service_request.title}"'
        )
        
        return Response(
            TaskApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED
        )


class TaskCandidatesListView(generics.ListAPIView):
    """
    List candidates/applicants for a specific task (for client)
    قائمة المتقدمين لمهمة معينة (للعميل)
    """
    serializer_class = TaskApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only task owner (client) can see candidates
        service_request_id = self.kwargs.get('pk')
        service_request = get_object_or_404(ServiceRequest, id=service_request_id)
        
        if service_request.client != self.request.user.profile:
            raise PermissionDenied("You can only view candidates for your own tasks")
        
        return TaskApplication.objects.filter(
            service_request=service_request,
            is_active=True
        ).select_related('worker__profile__user').order_by('-applied_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_worker(request, pk):
    """
    Accept a worker for the task (client accepts worker application)
    قبول عامل للمهمة (العميل يقبل تقدم العامل)
    """
    # Get service request
    service_request = get_object_or_404(ServiceRequest, id=pk)
    
    # Ensure user is the task owner
    if service_request.client != request.user.profile:
        raise PermissionDenied("You can only accept workers for your own tasks")
    
    # Ensure task is still published
    if service_request.status != 'published':
        raise ValidationError("Task is no longer available for acceptance")
    
    # Get worker ID from request
    worker_id = request.data.get('worker_id')
    if not worker_id:
        raise ValidationError("Worker ID is required")
    
    # Get the application
    application = get_object_or_404(
        TaskApplication,
        service_request=service_request,
        worker_id=worker_id,
        is_active=True,
        application_status='pending'
    )
    
    # Accept this worker
    application.application_status = 'accepted'
    application.responded_at = timezone.now()
    application.save()
    
    # Assign worker to task and change status
    service_request.assigned_worker = application.worker
    service_request.status = 'active'
    service_request.accepted_at = timezone.now()
    service_request.save()
    
    # Reject all other applications
    TaskApplication.objects.filter(
        service_request=service_request,
        is_active=True
    ).exclude(id=application.id).update(
        application_status='rejected',
        responded_at=timezone.now()
    )
    
    # Notify accepted worker
    TaskNotification.objects.create(
        recipient=application.worker.profile,
        service_request=service_request,
        task_application=application,
        notification_type='application_accepted',
        title='Candidature acceptée!',
        message=f'Votre candidature pour "{service_request.title}" a été acceptée!'
    )
    
    # Notify rejected workers
    rejected_applications = TaskApplication.objects.filter(
        service_request=service_request,
        application_status='rejected'
    )
    
    for rejected_app in rejected_applications:
        TaskNotification.objects.create(
            recipient=rejected_app.worker.profile,
            service_request=service_request,
            task_application=rejected_app,
            notification_type='application_rejected',
            title='Candidature non retenue',
            message=f'Votre candidature pour "{service_request.title}" n\'a pas été retenue cette fois.'
        )
    
    return Response({
        'message': 'Worker accepted successfully',
        'task_status': 'active',
        'assigned_worker': application.worker.user.get_full_name() or application.worker.user.username
    })


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_task_status(request, pk):
    """
    Update task status (work completion flow)
    تحديث حالة المهمة (تدفق إكمال العمل)
    """
    service_request = get_object_or_404(ServiceRequest, id=pk)
    new_status = request.data.get('status')
    
    if not new_status:
        raise ValidationError("Status is required")
    
    # Status change permissions and logic
    if new_status == 'work_completed':
        # Only assigned worker can mark work as completed
        if not hasattr(request.user.profile, 'worker_profile'):
            raise PermissionDenied("Only workers can mark work as completed")
        
        if service_request.assigned_worker != request.user.profile.worker_profile:
            raise PermissionDenied("Only the assigned worker can mark this work as completed")
        
        if service_request.status != 'active':
            raise ValidationError("Task must be active to mark as work completed")
        
        # Update status and timestamp
        service_request.status = 'work_completed'
        service_request.work_completed_at = timezone.now()
        service_request.save()
        
        # Notify client that work is completed
        TaskNotification.objects.create(
            recipient=service_request.client,
            service_request=service_request,
            notification_type='work_completed',
            title='Travail terminé',
            message=f'Le prestataire a terminé le travail pour "{service_request.title}". Veuillez vérifier et confirmer.'
        )
        
        return Response({'message': 'Work marked as completed. Waiting for client confirmation.'})
    
    elif new_status == 'completed':
        # Only client can confirm final completion
        if service_request.client != request.user.profile:
            raise PermissionDenied("Only the client can confirm task completion")
        
        if service_request.status != 'work_completed':
            raise ValidationError("Work must be marked as completed by worker first")
        
        # Final completion
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()
        
        # Update worker stats
        worker = service_request.assigned_worker
        worker.total_jobs_completed += 1
        worker.save()
        
        # Notify worker about completion confirmation
        TaskNotification.objects.create(
            recipient=worker.profile,
            service_request=service_request,
            notification_type='task_completed',
            title='Tâche confirmée terminée',
            message=f'Le client a confirmé la completion de "{service_request.title}". Félicitations!'
        )
        
        return Response({'message': 'Task completed successfully. Payment will be processed.'})
    
    elif new_status == 'cancelled':
        # Only client can cancel their own published tasks
        if service_request.client != request.user.profile:
            raise PermissionDenied("You can only cancel your own tasks")
        
        if service_request.status not in ['published', 'active']:
            raise ValidationError("Only published or active tasks can be cancelled")
        
        service_request.status = 'cancelled'
        service_request.cancelled_at = timezone.now()
        service_request.save()
        
        # Notify assigned worker if any
        if service_request.assigned_worker:
            TaskNotification.objects.create(
                recipient=service_request.assigned_worker.profile,
                service_request=service_request,
                notification_type='task_cancelled',
                title='Tâche annulée',
                message=f'La tâche "{service_request.title}" a été annulée par le client.'
            )
        
        return Response({'message': 'Task cancelled successfully'})
    
    else:
        raise ValidationError("Invalid status")


class TaskReviewCreateView(generics.CreateAPIView):
    """
    Create task review (client reviews completed task)
    إنشاء تقييم المهمة (العميل يقيم المهمة المكتملة)
    """
    serializer_class = TaskReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Get service request
        service_request_id = self.kwargs.get('pk')
        service_request = get_object_or_404(
            ServiceRequest, 
            id=service_request_id,
            status='completed'
        )
        
        # Ensure user is the client
        if service_request.client != self.request.user.profile:
            raise PermissionDenied("You can only review your own completed tasks")
        
        # Ensure no existing review
        if hasattr(service_request, 'review'):
            raise ValidationError("Task already reviewed")
        
        # Create review
        review = serializer.save(
            service_request=service_request,
            client=self.request.user.profile,
            worker=service_request.assigned_worker
        )
        
        # Notify worker about review
        TaskNotification.objects.create(
            recipient=service_request.assigned_worker.profile,
            service_request=service_request,
            notification_type='review_received',
            title='Nouvelle évaluation reçue',
            message=f'Vous avez reçu une évaluation de {review.rating} étoiles pour "{service_request.title}"'
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def task_stats(request):
    """
    Get task statistics for admin or user-specific stats
    إحصائيات المهام للأدمن أو إحصائيات خاصة بالمستخدم
    """
    user_profile = request.user.profile
    
    if user_profile.role == 'client':
        # Client task statistics
        stats = {
            'published': ServiceRequest.objects.filter(
                client=user_profile,
                status='published'
            ).count(),
            'active': ServiceRequest.objects.filter(
                client=user_profile,
                status='active'
            ).count(),
            'completed': ServiceRequest.objects.filter(
                client=user_profile,
                status='completed'
            ).count(),
            'cancelled': ServiceRequest.objects.filter(
                client=user_profile,
                status='cancelled'
            ).count(),
            'total_spent': 0,  # TODO: Calculate from completed tasks
        }
        
    elif user_profile.role == 'worker':
        # Worker task statistics
        try:
            worker_profile = user_profile.worker_profile
            stats = {
                'applications_sent': TaskApplication.objects.filter(
                    worker=worker_profile
                ).count(),
                'applications_pending': TaskApplication.objects.filter(
                    worker=worker_profile,
                    application_status='pending'
                ).count(),
                'applications_accepted': TaskApplication.objects.filter(
                    worker=worker_profile,
                    application_status='accepted'
                ).count(),
                'tasks_active': ServiceRequest.objects.filter(
                    assigned_worker=worker_profile,
                    status='active'
                ).count(),
                'tasks_completed': ServiceRequest.objects.filter(
                    assigned_worker=worker_profile,
                    status='completed'
                ).count(),
                'total_earned': 0,  # TODO: Calculate from completed tasks
            }
        except:
            stats = {}
    
    else:
        # Admin statistics
        stats = {
            'total_tasks': ServiceRequest.objects.count(),
            'published_tasks': ServiceRequest.objects.filter(status='published').count(),
            'active_tasks': ServiceRequest.objects.filter(status='active').count(),
            'completed_tasks': ServiceRequest.objects.filter(status='completed').count(),
            'cancelled_tasks': ServiceRequest.objects.filter(status='cancelled').count(),
            'total_applications': TaskApplication.objects.count(),
            'total_reviews': TaskReview.objects.count(),
            'average_rating': TaskReview.objects.aggregate(
                avg_rating=models.Avg('rating')
            )['avg_rating'] or 0,
        }
    
    return Response(stats)