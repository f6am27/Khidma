# notifications/admin_signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Q
from users.models import User
from .models import Notification, NotificationSettings


def get_admin_users():
    """الحصول على جميع المسؤولين النشطين"""
    return User.objects.filter(role='admin', is_active=True)


def create_admin_notification(notification_type, title, message, **kwargs):
    """
    إنشاء إشعار لجميع المسؤولين
    Create notification for all admins
    
    ✅ يتحقق من إعدادات الإشعارات قبل الإنشاء
    """
    admins = get_admin_users()
    notifications_created = []
    
    for admin in admins:
        # ✅ التحقق من إعدادات الإشعارات
        settings, _ = NotificationSettings.objects.get_or_create(
            user=admin,
            defaults={'notifications_enabled': True}
        )
        
        # ✅ إنشاء الإشعار فقط إذا كانت الإشعارات مفعّلة
        if settings.should_send_notification():
            notification = Notification.objects.create(
                recipient=admin,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )
            notifications_created.append(notification)
    
    return notifications_created


# ============================================
# Signal 1: New User
# ============================================
@receiver(post_save, sender=User)
def notify_admin_new_user(sender, instance, created, **kwargs):
    """
    إشعار عند تسجيل مستخدم جديد
    Notify admin when new user registers
    """
    if created and instance.role in ['client', 'worker']:
        role_name = 'Client' if instance.role == 'client' else 'Prestataire'
        user_name = instance.get_full_name() or instance.phone
        
        create_admin_notification(
            notification_type='new_user',
            title=f'Nouvel utilisateur: {role_name}',
            message=f'{user_name} vient de s\'inscrire en tant que {role_name}.'
        )


# ============================================
# Signal 2: New Report
# ============================================
@receiver(post_save, sender='chat.Report')
def notify_admin_new_report(sender, instance, created, **kwargs):
    """
    إشعار عند بلاغ جديد
    Notify admin when new report is created
    """
    if created:
        reporter_name = instance.reporter.get_full_name() or instance.reporter.phone
        reported_name = instance.reported_user.get_full_name() or instance.reported_user.phone
        reason_display = instance.get_reason_display()
        
        create_admin_notification(
            notification_type='new_report',
            title='Nouveau signalement',
            message=f'{reporter_name} a signale {reported_name} pour: {reason_display}'
        )


# ============================================
# Signal 3: Low Rating
# ============================================
@receiver(post_save, sender='tasks.TaskReview')
def notify_admin_low_rating(sender, instance, created, **kwargs):
    """
    إشعار عند تقييم سلبي (< 2 نجوم)
    Notify admin when low rating is given
    """
    if created and instance.rating < 2:
        worker_name = instance.worker.get_full_name() or instance.worker.phone
        task_title = instance.service_request.title
        
        create_admin_notification(
            notification_type='low_rating',
            title=f'Evaluation negative: {instance.rating}/5',
            message=f'{worker_name} a recu une note de {instance.rating}/5 pour "{task_title}"',
            related_task=instance.service_request
        )


# ============================================
# Signal 4: Large Payment
# # ============================================
# @receiver(post_save, sender='payments.Payment')
# def notify_admin_large_payment(sender, instance, created, **kwargs):
#     """
#     إشعار عند معاملة مالية كبيرة (> 10000 MRU)
#     Notify admin when large payment is made
#     """
#     if created and instance.amount > 10000:
#         payer_name = instance.payer.get_full_name() or instance.payer.phone
#         receiver_name = instance.receiver.get_full_name() or instance.receiver.phone
        
#         create_admin_notification(
#             notification_type='large_payment',
#             title=f'Transaction importante: {instance.amount} MRU',
#             message=f'Paiement de {instance.amount} MRU de {payer_name} a {receiver_name}',
#             related_task=instance.task if hasattr(instance, 'task') else None
#         )


# ============================================
# Signal 5: Task Completed
# ============================================
@receiver(post_save, sender='tasks.ServiceRequest')
def notify_admin_task_completed(sender, instance, created, update_fields, **kwargs):
    """
    إشعار عند إكمال مهمة
    Notify admin when task is completed
    """
    if not created and update_fields and 'status' in update_fields:
        if instance.status == 'completed':
            client_name = instance.client.get_full_name() or instance.client.phone
            worker_name = instance.assigned_worker.get_full_name() if instance.assigned_worker else 'Non assigne'
            
            create_admin_notification(
                notification_type='task_completed',
                title=f'Tache terminee: {instance.title}',
                message=f'Client: {client_name} | Prestataire: {worker_name} | Budget: {instance.budget} MRU',
                related_task=instance
            )