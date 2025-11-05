# notifications/utils.py
"""
دوال مساعدة لإنشاء الإشعارات مع Firebase
Enhanced notification utilities with Firebase integration
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from .models import Notification, NotificationSettings
from .firebase_service import firebase_service
from django.core.cache import cache
from datetime import timedelta
from tasks.models import ServiceRequest
from .admin_signals import create_admin_notification

logger = logging.getLogger('firebase_notifications')

def create_and_send_notification(
    recipient_user,
    notification_type: str,
    title: str,
    message: str,
    related_task=None,
    related_application=None,
    send_firebase: bool = True
) -> Dict[str, Any]:
    """
    إنشاء إشعار في قاعدة البيانات وإرساله عبر Firebase
    Create database notification and send via Firebase
    """
    
    try:
        # 1. التحقق من إعدادات الإشعارات للمستخدم
        settings, created = NotificationSettings.objects.get_or_create(
            user=recipient_user,
            defaults={'notifications_enabled': True}
        )
        
        if not settings.should_send_notification():
            logger.info(f"Notifications disabled for user {recipient_user.phone}")
            return {
                'success': True,
                'message': 'Notifications disabled for user',
                'notification_id': None,
                'firebase_sent': False
            }
        
        # 2. إنشاء الإشعار في قاعدة البيانات
        notification = Notification.objects.create(
            recipient=recipient_user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_task=related_task,
            related_application=related_application
        )
        
        logger.info(f"Database notification created: {notification.id}")
        
        # 3. إرسال عبر Firebase إذا مطلوب
        firebase_result = None
        if send_firebase and firebase_service.is_available():
            # بيانات إضافية للإشعار
            data = {
                'notification_id': str(notification.id),
                'notification_type': notification_type,
                'user_role': recipient_user.role,
                'timestamp': timezone.now().isoformat(),
            }
            
            # إضافة بيانات المهمة إذا وجدت
            if related_task:
                data.update({
                    'task_id': str(related_task.id),
                    'task_title': related_task.title[:50]  # أول 50 حرف
                })
            
            # إرسال الإشعار
            firebase_result = firebase_service.send_to_user(
                user=recipient_user,
                title=title,
                body=message,
                data=data
            )
            
            if firebase_result.get('success'):
                logger.info(f"Firebase notification sent to user {recipient_user.phone}")
            else:
                logger.error(f"Firebase sending failed: {firebase_result.get('error')}")
        
        return {
            'success': True,
            'notification_id': notification.id,
            'firebase_sent': firebase_result.get('success', False) if firebase_result else False,
            'firebase_result': firebase_result,
            'message': 'Notification created and sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'notification_id': None,
            'firebase_sent': False
        }


# ========================================
# دوال محددة لكل نوع إشعار - محسّنة
# ========================================

def notify_task_published(client_user, task):
    """إشعار نشر المهمة للعميل"""
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='task_published',
        title='Tâche publiée avec succès',
        message=f'Votre demande "{task.title}" a été publiée et est maintenant visible par les prestataires.',
        related_task=task
    )

def notify_worker_applied(client_user, worker_user, task, application):
    """إشعار تقدم العامل للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='worker_applied',
        title='Nouvelle candidature reçue',
        message=f'{worker_name} souhaite effectuer votre tâche "{task.title}". Consultez son profil et acceptez l\'offre.',
        related_task=task,
        related_application=application
    )

def notify_application_accepted(worker_user, task, client_user):
    """إشعار قبول الطلب للعامل"""
    client_name = client_user.get_full_name() or client_user.phone
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='application_accepted',
        title='Candidature acceptée!',
        message=f'Félicitations! Votre candidature pour "{task.title}" a été acceptée par {client_name}.',
        related_task=task
    )

def notify_application_rejected(worker_user, task):
    """إشعار رفض الطلب للعامل"""
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='application_rejected',
        title='Candidature non retenue',
        message=f'Votre candidature pour "{task.title}" n\'a pas été retenue cette fois. Continuez à postuler!',
        related_task=task
    )

def notify_task_completed(client_user, worker_user, task):
    """إشعار اكتمال المهمة للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='task_completed',
        title='Service terminé',
        message=f'{worker_name} a marqué votre tâche "{task.title}" comme terminée. Confirmez et effectuez le paiement.',
        related_task=task
    )

def notify_work_started(client_user, worker_user, task):
    """إشعار العميل ببدء العامل في العمل"""
    worker_name = worker_user.get_full_name() or worker_user.phone or "Le prestataire"
    
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='work_started',
        title='Travail commencé',
        message=f'{worker_name} a commencé à travailler sur votre demande "{task.title}".',
        related_task=task
    )

def notify_payment_received(client_user, task, amount):
    """إشعار استلام الدفع للعميل"""
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='payment_received',
        title='Paiement confirmé',
        message=f'Votre paiement de {amount} MRU pour le service "{task.title}" a été effectué avec succès.',
        related_task=task
    )

def notify_payment_sent(worker_user, task, amount):
    """إشعار إرسال الدفع للعامل"""
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='payment_sent',
        title='Paiement reçu',
        message=f'Vous avez reçu un paiement de {amount} MRU pour votre service "{task.title}". Merci pour votre excellent travail!',
        related_task=task
    )

def notify_new_task_available(worker_user, task):
    """إشعار مهمة جديدة متاحة للعامل"""
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='new_task_available',
        title='Nouvelle tâche disponible',
        message=f'Une nouvelle tâche "{task.title}" est disponible dans votre zone pour {task.budget} MRU.',
        related_task=task
    )

def notify_message_received(recipient_user, sender_user, task, message_preview=""):
    """إشعار استلام رسالة"""
    sender_name = sender_user.get_full_name() or sender_user.phone or "Un utilisateur"
    
    # تجهيز نص الإشعار حسب وجود المهمة
    if task:
        message_text = f'{sender_name} vous a envoyé un message concernant "{task.title}".'
    else:
        message_text = f'{sender_name} vous a envoyé un message.'
    
    if message_preview:
        message_text += f' "{message_preview[:50]}..."'
    
    return create_and_send_notification(
        recipient_user=recipient_user,
        notification_type='message_received',
        title='Nouveau message reçu',
        message=message_text,
        related_task=task
    )

def notify_service_reminder(client_user, worker_user, task, scheduled_time):
    """إشعار تذكير الخدمة للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    time_str = scheduled_time.strftime('%d/%m/%Y à %H:%M')
    
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='service_reminder',
        title='Rappel de service',
        message=f'Votre service "{task.title}" avec {worker_name} est programmé pour {time_str}. N\'oubliez pas!',
        related_task=task
    )

def notify_service_cancelled(client_user, worker_user, task, reason=""):
    """إشعار إلغاء الخدمة للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    message_text = f'{worker_name} a dû annuler votre rendez-vous "{task.title}". Il vous contactera pour reprogrammer.'
    
    if reason:
        message_text += f' Motif: {reason}'
    
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='service_cancelled',
        title='Service annulé',
        message=message_text,
        related_task=task
    )


# ========================================
# دوال مساعدة إضافية
# ========================================

def bulk_notify_workers(worker_users, task):
    """إشعار مجموعة من العمال بمهمة جديدة"""
    results = []
    
    for worker_user in worker_users:
        result = notify_new_task_available(worker_user, task)
        results.append({
            'worker_id': worker_user.id,
            'worker_phone': worker_user.phone,
            'success': result['success'],
            'notification_id': result.get('notification_id'),
            'firebase_sent': result.get('firebase_sent', False)
        })
    
    successful_notifications = len([r for r in results if r['success']])
    logger.info(f"Bulk notification sent to {successful_notifications}/{len(worker_users)} workers for task {task.id}")
    
    return {
        'total_workers': len(worker_users),
        'successful_notifications': successful_notifications,
        'results': results
    }

def cleanup_old_notifications(days=90):
    """تنظيف الإشعارات القديمة"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # حذف الإشعارات المقروءة القديمة
    deleted_count = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old notifications")
    return deleted_count

def get_notification_stats(user):
    """احصائيات الإشعارات للمستخدم"""
    notifications = Notification.objects.filter(recipient=user)
    
    return {
        'total': notifications.count(),
        'unread': notifications.filter(is_read=False).count(),
        'today': notifications.filter(
            created_at__date=timezone.now().date()
        ).count(),
        'this_week': notifications.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
    }


logger = logging.getLogger(__name__)

PAYMENT_CHECK_CACHE_KEY = 'last_payment_pending_check'
PAYMENT_CHECK_INTERVAL_HOURS = 24  # كل 24 ساعة


def check_pending_payments():
    """
    فحص الدفعات المعلقة وإنشاء إشعارات
    Check pending payments and create notifications
    """
    try:
        # التحقق من آخر فحص
        last_check = cache.get(PAYMENT_CHECK_CACHE_KEY)
        now = timezone.now()
        
        if last_check:
            last_check_time = timezone.datetime.fromisoformat(last_check)
            hours_since_check = (now - last_check_time).total_seconds() / 3600
            
            # إذا لم يمر 24 ساعة، لا تفحص
            if hours_since_check < PAYMENT_CHECK_INTERVAL_HOURS:
                return
        
        # حساب 48 ساعة قبل الآن
        cutoff_time = now - timedelta(hours=48)
        
        # البحث عن المهام المعلقة
        pending_tasks = ServiceRequest.objects.filter(
            status='work_completed',
            work_completed_at__lte=cutoff_time
        ).exclude(
            payment__status='completed'
        )
        
        # إنشاء إشعارات
        count = 0
        for task in pending_tasks:
            client_name = task.client.get_full_name() or task.client.phone
            worker_name = task.assigned_worker.get_full_name() if task.assigned_worker else 'Non assigné'
            
            # حساب عدد الساعات
            hours_passed = int((now - task.work_completed_at).total_seconds() / 3600)
            
            # تحقق من عدم وجود إشعار سابق لنفس المهمة
            from .models import Notification
            existing = Notification.objects.filter(
                notification_type='payment_pending',
                related_task=task
            ).exists()
            
            if not existing:
                create_admin_notification(
                    notification_type='payment_pending',
                    title=f'⏰ Paiement en attente: {task.title}',
                    message=f'Travail terminé il y a {hours_passed}h. Client: {client_name} | Prestataire: {worker_name} | Montant: {task.budget} MRU',
                    related_task=task
                )
                count += 1
        
        # حفظ وقت الفحص الحالي
        cache.set(PAYMENT_CHECK_CACHE_KEY, now.isoformat(), timeout=None)
        
        logger.info(f'✅ Payment pending check completed. {count} notifications created.')
        
    except Exception as e:
        logger.error(f'❌ Error checking pending payments: {str(e)}')


def trigger_payment_check_if_needed():
    """
    تشغيل فحص الدفعات إذا مر الوقت المحدد
    Trigger payment check if interval has passed
    """
    check_pending_payments()