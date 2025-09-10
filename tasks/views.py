# tasks/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
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
        # Ensure user is a client
        if self.request.user.role != 'client':
            raise PermissionDenied("Only clients can create service requests")
        
        # Create the service request
        service_request = serializer.save()
        
        # Send notification to relevant workers (async in production)
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
    serializer_class = ServiceRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']
    
    def get_queryset(self):
        if self.request.user.role != 'client':
            return ServiceRequest.objects.none()
        
        return ServiceRequest.objects.filter(
            client=self.request.user
        ).select_related('service_category', 'assigned_worker')


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
       
       # أظهر جميع المهام المنشورة (بدلاً من التقييد بخدمات العامل)
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
       
       sort_by = self.request.query_params.get('sort_by', 'latest')
       if sort_by == 'budget_high':
           queryset = queryset.order_by('-budget')
       elif sort_by == 'budget_low':
           queryset = queryset.order_by('budget')
       elif sort_by == 'urgent':
           queryset = queryset.order_by('-is_urgent', '-created_at')
       else:
           queryset = queryset.order_by('-created_at')
       
       return queryset
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
        
        # Use request.user directly instead of worker_profile
        if TaskApplication.objects.filter(
            service_request=service_request,
            worker=request.user,
            is_active=True
        ).exists():
            raise ValidationError("You have already applied for this task")
        
        if not request.user.worker_services.filter(
            category=service_request.service_category
        ).exists():
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
    
    # assigned_worker is now the User object directly
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
            title='Travail terminé',
            message=f'Le prestataire a terminé le travail pour "{service_request.title}". Veuillez vérifier et confirmer.'
        )
        
        return Response({'message': 'Work marked as completed. Waiting for client confirmation.'})
    
    elif new_status == 'completed':
        if service_request.client != request.user:
            raise PermissionDenied("Only the client can confirm task completion")
        
        if service_request.status != 'work_completed':
            raise ValidationError("Work must be marked as completed by worker first")
        
        service_request.status = 'completed'
        service_request.completed_at = timezone.now()
        service_request.save()
        
        worker = service_request.assigned_worker
        worker.total_jobs_completed += 1
        worker.save()
        
        TaskNotification.objects.create(
            recipient=worker,
            service_request=service_request,
            notification_type='task_completed',
            title='Tâche confirmée terminée',
            message=f'Le client a confirmé la completion de "{service_request.title}". Félicitations!'
        )
        
        return Response({'message': 'Task completed successfully. Payment will be processed.'})
    
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
                title='Tâche annulée',
                message=f'La tâche "{service_request.title}" a été annulée par le client.'
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
            'published': ServiceRequest.objects.filter(
                client=user,
                status='published'
            ).count(),
            'active': ServiceRequest.objects.filter(
                client=user,
                status='active'
            ).count(),
            'completed': ServiceRequest.objects.filter(
                client=user,
                status='completed'
            ).count(),
            'cancelled': ServiceRequest.objects.filter(
                client=user,
                status='cancelled'
            ).count(),
            'total_spent': 0,
        }
        
    elif user.role == 'worker':
        stats = {
            'applications_sent': TaskApplication.objects.filter(
                worker=user
            ).count(),
            'applications_pending': TaskApplication.objects.filter(
                worker=user,
                application_status='pending'
            ).count(),
            'applications_accepted': TaskApplication.objects.filter(
                worker=user,
                application_status='accepted'
            ).count(),
            'tasks_active': ServiceRequest.objects.filter(
                assigned_worker=user,
                status='active'
            ).count(),
            'tasks_completed': ServiceRequest.objects.filter(
                assigned_worker=user,
                status='completed'
            ).count(),
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
            'average_rating': TaskReview.objects.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
        }
    
    return Response(stats)
