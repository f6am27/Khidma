# notifications/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import Notification, NotificationSettings
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationSettingsSerializer,
    NotificationStatsSerializer,
    BulkNotificationSerializer,
    NotificationCreateSerializer
)


class NotificationListView(generics.ListAPIView):
    """
    قائمة الإشعارات الموحدة للعمال والعملاء
    Unified notification list for workers and clients
    """
    serializer_class = NotificationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_read']
    
    def get_queryset(self):
        """الحصول على إشعارات المستخدم الحالي فقط"""
        user = self.request.user
        
        queryset = Notification.objects.filter(
            recipient=user
        ).select_related(
            'related_task',
            'related_application',
            'recipient'
        ).order_by('-created_at')
        
        # فلترة حسب حالة القراءة
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
        
        # فلترة حسب نوع الإشعار
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # فلترة حسب التاريخ
        days = self.request.query_params.get('days')
        if days:
            try:
                days_int = int(days)
                date_from = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(created_at__gte=date_from)
            except ValueError:
                pass
        
        return queryset


class NotificationDetailView(generics.RetrieveAPIView):
    """
    تفاصيل إشعار محدد
    Specific notification details
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """التأكد من أن المستخدم يملك الإشعار"""
        return Notification.objects.filter(recipient=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """عرض الإشعار وتحديده كمقروء تلقائياً"""
        instance = self.get_object()
        
        # تحديد كمقروء إذا لم يكن مقروءاً
        if not instance.is_read:
            instance.mark_as_read()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    """
    تحديد إشعار كمقروء
    Mark notification as read
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marquée comme lue',
            'notification_id': notification_id,
            'is_read': True,
            'read_at': notification.read_at
        })
    except Notification.DoesNotExist:
        raise NotFound("Notification non trouvée")


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_as_unread(request, notification_id):
    """
    تحديد إشعار كغير مقروء
    Mark notification as unread
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=['is_read', 'read_at'])
        
        return Response({
            'message': 'Notification marquée comme non lue',
            'notification_id': notification_id,
            'is_read': False
        })
    except Notification.DoesNotExist:
        raise NotFound("Notification non trouvée")


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_as_read(request):
    """
    تحديد جميع الإشعارات كمقروءة
    Mark all notifications as read
    """
    updated_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'message': f'{updated_count} notifications marquées comme lues',
        'updated_count': updated_count
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_notification(request, notification_id):
    """
    حذف إشعار محدد
    Delete specific notification
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.delete()
        
        return Response({
            'message': 'Notification supprimée avec succès',
            'notification_id': notification_id
        })
    except Notification.DoesNotExist:
        raise NotFound("Notification non trouvée")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_notification_action(request):
    """
    إجراءات مجمعة على الإشعارات
    Bulk actions on notifications
    """
    serializer = BulkNotificationSerializer(
        data=request.data,
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    
    notification_ids = serializer.validated_data['notification_ids']
    action = serializer.validated_data['action']
    
    notifications = Notification.objects.filter(
        id__in=notification_ids,
        recipient=request.user
    )
    
    if action == 'mark_read':
        updated_count = notifications.update(
            is_read=True,
            read_at=timezone.now()
        )
        message = f'{updated_count} notifications marquées comme lues'
    
    elif action == 'mark_unread':
        updated_count = notifications.update(
            is_read=False,
            read_at=None
        )
        message = f'{updated_count} notifications marquées comme non lues'
    
    elif action == 'delete':
        deleted_count = notifications.delete()[0]
        message = f'{deleted_count} notifications supprimées'
        updated_count = deleted_count
    
    return Response({
        'message': message,
        'action': action,
        'affected_count': updated_count,
        'notification_ids': notification_ids
    })


class NotificationStatsView(generics.RetrieveAPIView):
    """
    إحصائيات الإشعارات للمستخدم
    User notification statistics
    """
    serializer_class = NotificationStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """حساب إحصائيات الإشعارات"""
        user = self.request.user
        notifications = Notification.objects.filter(recipient=user)
        
        # إحصائيات عامة
        total_notifications = notifications.count()
        unread_notifications = notifications.filter(is_read=False).count()
        read_notifications = total_notifications - unread_notifications
        
        # إحصائيات حسب التاريخ
        today = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)
        
        notifications_today = notifications.filter(
            created_at__date=today
        ).count()
        
        notifications_this_week = notifications.filter(
            created_at__gte=week_ago
        ).count()
        
        # إحصائيات حسب النوع
        task_notifications = notifications.filter(
            notification_type__in=[
                'task_published', 'task_completed', 'new_task_available',
                'application_accepted', 'application_rejected'
            ]
        ).count()
        
        message_notifications = notifications.filter(
            notification_type='message_received'
        ).count()
        
        payment_notifications = notifications.filter(
            notification_type__in=['payment_received', 'payment_sent']
        ).count()
        
        return {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': read_notifications,
            'notifications_today': notifications_today,
            'notifications_this_week': notifications_this_week,
            'task_notifications': task_notifications,
            'message_notifications': message_notifications,
            'payment_notifications': payment_notifications,
        }


class NotificationSettingsView(generics.RetrieveUpdateAPIView):
    """
    إعدادات الإشعارات للمستخدم
    User notification settings
    """
    serializer_class = NotificationSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'patch']  # ✅ إضافة PATCH
    
    def get_object(self):
        """الحصول على إعدادات الإشعارات أو إنشاؤها"""
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user,
            defaults={'notifications_enabled': True}
        )
        if created:
            print(f'✅ Created notification settings for user: {self.request.user.phone}')
        return settings
    
    def update(self, request, *args, **kwargs):
        """تحديث الإعدادات مع logging"""
        instance = self.get_object()
        print(f'📍 Updating settings for user: {request.user.phone}')
        print(f'📩 Request data: {request.data}')
        
        response = super().update(request, *args, **kwargs)
        
        print(f'✅ Settings updated: notifications_enabled = {instance.notifications_enabled}')
        
        return response


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_types(request):
    """
    قائمة أنواع الإشعارات المتاحة حسب دور المستخدم
    Available notification types based on user role
    """
    user_role = request.user.role
    
    if user_role == 'client':
        types = [
            {'type': 'task_published', 'name': 'Tâche publiée'},
            {'type': 'worker_applied', 'name': 'Prestataire candidat'},
            {'type': 'task_completed', 'name': 'Tâche terminée'},
            {'type': 'payment_received', 'name': 'Paiement reçu'},
            {'type': 'message_received', 'name': 'Message reçu'},
            {'type': 'service_reminder', 'name': 'Rappel de service'},
            {'type': 'service_cancelled', 'name': 'Service annulé'},
        ]
    elif user_role == 'worker':
        types = [
            {'type': 'new_task_available', 'name': 'Nouvelle tâche disponible'},
            {'type': 'application_accepted', 'name': 'Candidature acceptée'},
            {'type': 'application_rejected', 'name': 'Candidature rejetée'},
            {'type': 'payment_sent', 'name': 'Paiement envoyé'},
            {'type': 'message_received', 'name': 'Message reçu'},
        ]
    else:
        types = []
    
    return Response({
        'user_role': user_role,
        'notification_types': types
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_all_notifications(request):
    """
    حذف جميع الإشعارات المقروءة
    Clear all read notifications
    """
    deleted_count = Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()[0]
    
    return Response({
        'message': f'{deleted_count} notifications supprimées',
        'deleted_count': deleted_count
    })


# Admin Views (للإدارة)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def create_notification(request):
    """
    إنشاء إشعار جديد (للإدارة)
    Create new notification (admin only)
    """
    serializer = NotificationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    notification = serializer.save()
    
    return Response({
        'message': 'Notification créée avec succès',
        'notification_id': notification.id,
        'recipient': notification.recipient.username,
        'type': notification.notification_type
    }, status=status.HTTP_201_CREATED)