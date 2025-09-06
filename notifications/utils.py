# notifications/utils.py
from django.utils import timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# قوالب الترجمة الفرنسية (المرحلة الحالية)
FRENCH_TRANSLATIONS = {
    # إشعارات العملاء
    'notifications.task_published.title': 'Tâche publiée avec succès',
    'notifications.task_published.message': 'Votre demande "{task_title}" a été publiée et est maintenant visible par les prestataires.',
    
    'notifications.worker_applied.title': 'Nouvelle candidature reçue',
    'notifications.worker_applied.message': '{worker_name} souhaite effectuer votre tâche "{task_title}". Consultez son profil et acceptez l\'offre.',
    
    'notifications.task_completed.title': 'Service terminé',
    'notifications.task_completed.message': '{worker_name} a marqué votre tâche "{task_title}" comme terminée. Confirmez et effectuez le paiement.',
    
    'notifications.payment_received.title': 'Paiement confirmé',
    'notifications.payment_received.message': 'Votre paiement de {amount} MRU pour le service "{task_title}" a été effectué avec succès.',
    
    'notifications.message_received.title': 'Nouveau message reçu',
    'notifications.message_received.message': '{sender_name} vous a envoyé un message concernant votre demande "{task_title}".',
    
    'notifications.service_reminder.title': 'Rappel de service',
    'notifications.service_reminder.message': 'Votre service "{task_title}" avec {worker_name} est programmé pour {scheduled_time}. N\'oubliez pas!',
    
    'notifications.service_cancelled.title': 'Service annulé',
    'notifications.service_cancelled.message': '{worker_name} a dû annuler votre rendez-vous "{task_title}" prévu pour {scheduled_time}. Il vous contactera pour reprogrammer.',
    
    # إشعارات العمال
    'notifications.new_task_available.title': 'Nouvelle tâche disponible',
    'notifications.new_task_available.message': 'Une nouvelle tâche "{task_title}" est disponible dans votre zone pour {budget} MRU.',
    
    'notifications.application_accepted.title': 'Candidature acceptée!',
    'notifications.application_accepted.message': 'Félicitations! Votre candidature pour "{task_title}" a été acceptée par {client_name}.',
    
    'notifications.application_rejected.title': 'Candidature non retenue',
    'notifications.application_rejected.message': 'Votre candidature pour "{task_title}" n\'a pas été retenue cette fois. Continuez à postuler!',
    
    'notifications.payment_sent.title': 'Paiement reçu',
    'notifications.payment_sent.message': 'Vous avez reçu un paiement de {amount} MRU pour votre service "{task_title}". Merci pour votre excellent travail!',
}

# قوالب العربية (للمستقبل)
ARABIC_TRANSLATIONS = {
    # سيتم إضافتها لاحقاً
    'notifications.task_published.title': 'تم نشر المهمة بنجاح',
    'notifications.task_published.message': 'تم نشر طلبك "{task_title}" وهو متاح الآن للعمال.',
    
    'notifications.worker_applied.title': 'طلب جديد للعمل',
    'notifications.worker_applied.message': '{worker_name} يرغب في تنفيذ مهمتك "{task_title}". اطلع على ملفه الشخصي واقبل العرض.',
    
    # باقي الترجمات العربية...
}

# قوالب الإنجليزية (للمستقبل)
ENGLISH_TRANSLATIONS = {
    # سيتم إضافتها لاحقاً
    'notifications.task_published.title': 'Task published successfully',
    'notifications.task_published.message': 'Your request "{task_title}" has been published and is now visible to service providers.',
    
    # باقي الترجمات الإنجليزية...
}

# خريطة اللغات
LANGUAGE_TRANSLATIONS = {
    'fr': FRENCH_TRANSLATIONS,
    'ar': ARABIC_TRANSLATIONS,
    'en': ENGLISH_TRANSLATIONS,
}


def get_translated_notification(title_key: str, message_key: str, context_data: Dict[str, Any], language: str = 'fr') -> Dict[str, str]:
    """
    الحصول على الإشعار المترجم مع استبدال المتغيرات
    Get translated notification with variable substitution
    """
    translations = LANGUAGE_TRANSLATIONS.get(language, FRENCH_TRANSLATIONS)
    
    # الحصول على القوالب
    title_template = translations.get(title_key, title_key)
    message_template = translations.get(message_key, message_key)
    
    try:
        # استبدال المتغيرات في القوالب
        title = title_template.format(**context_data) if context_data else title_template
        message = message_template.format(**context_data) if context_data else message_template
        
        return {
            'title': title,
            'message': message
        }
    except KeyError as e:
        logger.warning(f"Missing context variable {e} for notification {title_key}")
        return {
            'title': title_template,
            'message': message_template
        }
    except Exception as e:
        logger.error(f"Error translating notification: {e}")
        return {
            'title': title_key,
            'message': message_key
        }


def create_task_published_notification(client_profile, task):
    """إنشاء إشعار نشر المهمة للعميل"""
    from .models import Notification
    
    context_data = {
        'task_title': task.title,
        'client_name': client_profile.user.get_full_name() or client_profile.user.username,
    }
    
    return Notification.create_for_client(
        client=client_profile,
        notification_type='task_published',
        context_data=context_data,
        related_task=task,
        priority='medium'
    )


def create_worker_applied_notification(client_profile, worker_profile, task, application):
    """إنشاء إشعار تقدم العامل للعميل"""
    from .models import Notification
    
    context_data = {
        'worker_name': worker_profile.user.get_full_name() or worker_profile.user.username,
        'task_title': task.title,
        'client_name': client_profile.user.get_full_name() or client_profile.user.username,
    }
    
    return Notification.create_for_client(
        client=client_profile,
        notification_type='worker_applied',
        context_data=context_data,
        related_task=task,
        related_worker=worker_profile,
        related_application=application,
        priority='high'
    )


def create_new_task_notification(worker_profile, task):
    """إنشاء إشعار مهمة جديدة للعامل"""
    from .models import Notification
    
    context_data = {
        'task_title': task.title,
        'budget': float(task.budget),  # تحويل Decimal إلى float
        'client_name': task.client.user.get_full_name() or task.client.user.username,
    }
    
    return Notification.create_for_worker(
        worker_profile=worker_profile,
        notification_type='new_task_available',
        context_data=context_data,
        related_task=task,
        priority='medium'
    )
def create_application_accepted_notification(worker_profile, task, client_profile):
    """إنشاء إشعار قبول الطلب للعامل"""
    from .models import Notification
    
    context_data = {
        'task_title': task.title,
        'client_name': client_profile.user.get_full_name() or client_profile.user.username,
        'budget': float(task.budget),  # تحويل Decimal إلى float
    }
    
    return Notification.create_for_worker(
        worker_profile=worker_profile,
        notification_type='application_accepted',
        context_data=context_data,
        related_task=task,
        priority='high'
    )

def create_application_rejected_notification(worker_profile, task):
    """إنشاء إشعار رفض الطلب للعامل"""
    from .models import Notification
    
    context_data = {
        'task_title': task.title,
    }
    
    return Notification.create_for_worker(
        worker_profile=worker_profile,
        notification_type='application_rejected',
        context_data=context_data,
        related_task=task,
        priority='low'
    )


def create_task_completed_notification(client_profile, worker_profile, task):
    """إنشاء إشعار اكتمال المهمة للعميل"""
    from .models import Notification
    
    context_data = {
        'worker_name': worker_profile.user.get_full_name() or worker_profile.user.username,
        'task_title': task.title,
    }
    
    return Notification.create_for_client(
        client=client_profile,
        notification_type='task_completed',
        context_data=context_data,
        related_task=task,
        related_worker=worker_profile,
        priority='high'
    )


def create_payment_notification(recipient_profile, task, amount, is_client=True):
    """إنشاء إشعار الدفع للعميل أو العامل"""
    from .models import Notification
    
    context_data = {
        'amount': float(amount),  # تحويل Decimal إلى float
        'task_title': task.title,
    }
    
    if is_client:
        return Notification.create_for_client(
            client=recipient_profile,
            notification_type='payment_received',
            context_data=context_data,
            related_task=task,
            priority='medium'
        )
    else:
        return Notification.create_for_worker(
            worker_profile=recipient_profile,
            notification_type='payment_sent',
            context_data=context_data,
            related_task=task,
            priority='medium'
        )
def create_message_notification(recipient_profile, sender_profile, task, is_client=True):
    """إنشاء إشعار رسالة جديدة"""
    from .models import Notification
    
    context_data = {
        'sender_name': sender_profile.user.get_full_name() or sender_profile.user.username,
        'task_title': task.title,
    }
    
    if is_client:
        return Notification.create_for_client(
            client=recipient_profile,
            notification_type='message_received',
            context_data=context_data,
            related_task=task,
            priority='medium'
        )
    else:
        return Notification.create_for_worker(
            worker_profile=recipient_profile,
            notification_type='message_received',
            context_data=context_data,
            related_task=task,
            priority='medium'
        )


def create_service_reminder_notification(client_profile, worker_profile, task, scheduled_time):
    """إنشاء إشعار تذكير الخدمة للعميل"""
    from .models import Notification
    
    context_data = {
        'task_title': task.title,
        'worker_name': worker_profile.user.get_full_name() or worker_profile.user.username,
        'scheduled_time': scheduled_time.strftime('%d/%m/%Y à %H:%M'),
    }
    
    return Notification.create_for_client(
        client=client_profile,
        notification_type='service_reminder',
        context_data=context_data,
        related_task=task,
        related_worker=worker_profile,
        priority='medium'
    )


def create_service_cancelled_notification(client_profile, worker_profile, task, scheduled_time):
    """إنشاء إشعار إلغاء الخدمة للعميل"""
    from .models import Notification
    
    context_data = {
        'worker_name': worker_profile.user.get_full_name() or worker_profile.user.username,
        'task_title': task.title,
        'scheduled_time': scheduled_time.strftime('%d/%m/%Y à %H:%M'),
    }
    
    return Notification.create_for_client(
        client=client_profile,
        notification_type='service_cancelled',
        context_data=context_data,
        related_task=task,
        related_worker=worker_profile,
        priority='high'
    )


def notify_workers_new_task(task):
    """إشعار العمال المؤهلين بمهمة جديدة"""
    from workers.models import WorkerProfile
    from .models import NotificationSettings
    
    # العثور على العمال المؤهلين
    qualified_workers = WorkerProfile.objects.filter(
        services__category=task.service_category,
        is_available=True,
        profile__onboarding_completed=True
    ).distinct()
    
    notifications_created = 0
    
    for worker in qualified_workers:
        # التحقق من إعدادات الإشعارات
        settings, _ = NotificationSettings.objects.get_or_create(
            user=worker.profile,
            defaults={'notifications_enabled': True}
        )
        
        if settings.should_send_notification('new_task_available'):
            create_new_task_notification(worker, task)
            notifications_created += 1
    
    logger.info(f"Created {notifications_created} new task notifications for task {task.id}")
    return notifications_created


def cleanup_expired_notifications():
    """تنظيف الإشعارات منتهية الصلاحية"""
    from .models import Notification
    
    expired_count = Notification.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()[0]
    
    logger.info(f"Cleaned up {expired_count} expired notifications")
    return expired_count


def get_user_language(user_profile):
    """الحصول على لغة المستخدم المفضلة"""
    # من إعدادات العميل إذا كان عميل
    if hasattr(user_profile, 'client_profile'):
        return user_profile.client_profile.preferred_language
    
    # من إعدادات العامل إذا كان عامل (سيأتي لاحقاً)
    if hasattr(user_profile, 'worker_profile'):
        # return user_profile.worker_profile.preferred_language
        pass
    
    # افتراضي
    return 'fr'