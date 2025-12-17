"""
دوال مساعدة لإنشاء الإشعارات مع Firebase - مع دعم اللغات المتعددة
Enhanced notification utilities with multilingual support
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from .models import Notification, NotificationSettings
from .firebase_service import firebase_service

logger = logging.getLogger('firebase_notifications')

# ========================================
# قاموس الترجمات للإشعارات
# ========================================

NOTIFICATION_TRANSLATIONS = {
    'task_published': {
        'title': {
            'ar': 'تم نشر المهمة بنجاح',
            'fr': 'Tâche publiée avec succès',
            'en': 'Task Published Successfully'
        },
        'message': {
            'ar': 'تم نشر طلبك "{title}" وهو الآن مرئي للمزودين.',
            'fr': 'Votre demande "{title}" a été publiée et est maintenant visible par les prestataires.',
            'en': 'Your request "{title}" has been published and is now visible to providers.'
        }
    },
    'worker_applied': {
        'title': {
            'ar': 'طلب جديد مستلم',
            'fr': 'Nouvelle candidature reçue',
            'en': 'New Application Received'
        },
        'message': {
            'ar': '{worker_name} يرغب في تنفيذ مهمتك "{title}". راجع ملفه الشخصي واقبل العرض.',
            'fr': '{worker_name} souhaite effectuer votre tâche "{title}". Consultez son profil et acceptez l\'offre.',
            'en': '{worker_name} wants to perform your task "{title}". Review their profile and accept the offer.'
        }
    },
    'application_accepted': {
        'title': {
            'ar': 'تم قبول الطلب!',
            'fr': 'Candidature acceptée!',
            'en': 'Application Accepted!'
        },
        'message': {
            'ar': 'تهانينا! تم قبول طلبك لـ "{title}" من قبل {client_name}.',
            'fr': 'Félicitations! Votre candidature pour "{title}" a été acceptée par {client_name}.',
            'en': 'Congratulations! Your application for "{title}" has been accepted by {client_name}.'
        }
    },
    'application_rejected': {
        'title': {
            'ar': 'لم يتم اختيار الطلب',
            'fr': 'Candidature non retenue',
            'en': 'Application Not Selected'
        },
        'message': {
            'ar': 'لم يتم اختيار طلبك لـ "{title}" هذه المرة. استمر في التقديم!',
            'fr': 'Votre candidature pour "{title}" n\'a pas été retenue cette fois. Continuez à postuler!',
            'en': 'Your application for "{title}" was not selected this time. Keep applying!'
        }
    },
    'task_completed': {
        'title': {
            'ar': 'اكتمل الخدمة',
            'fr': 'Service terminé',
            'en': 'Service Completed'
        },
        'message': {
            'ar': '{worker_name} قام بوضع علامة على مهمتك "{title}" على أنها مكتملة. قم بالتأكيد والدفع.',
            'fr': '{worker_name} a marqué votre tâche "{title}" comme terminée. Confirmez et effectuez le paiement.',
            'en': '{worker_name} has marked your task "{title}" as completed. Confirm and make payment.'
        }
    },
    'work_started': {
        'title': {
            'ar': 'بدأ العمل',
            'fr': 'Travail commencé',
            'en': 'Work Started'
        },
        'message': {
            'ar': '{worker_name} بدأ العمل على طلبك "{title}".',
            'fr': '{worker_name} a commencé à travailler sur votre demande "{title}".',
            'en': '{worker_name} has started working on your request "{title}".'
        }
    },
    'payment_received': {
        'title': {
            'ar': 'تم تأكيد الدفع',
            'fr': 'Paiement confirmé',
            'en': 'Payment Confirmed'
        },
        'message': {
            'ar': 'تم الدفع بنجاح {amount} أوقية للخدمة "{title}".',
            'fr': 'Votre paiement de {amount} MRU pour le service "{title}" a été effectué avec succès.',
            'en': 'Your payment of {amount} MRU for service "{title}" was successful.'
        }
    },
    'payment_sent': {
        'title': {
            'ar': 'تم استلام الدفع',
            'fr': 'Paiement reçu',
            'en': 'Payment Received'
        },
        'message': {
            'ar': 'لقد استلمت دفعة {amount} أوقية لخدمتك "{title}". شكراً لعملك الممتاز!',
            'fr': 'Vous avez reçu un paiement de {amount} MRU pour votre service "{title}". Merci pour votre excellent travail!',
            'en': 'You have received a payment of {amount} MRU for your service "{title}". Thank you for your excellent work!'
        }
    },
    'new_task_available': {
        'title': {
            'ar': 'مهمة جديدة متاحة',
            'fr': 'Nouvelle tâche disponible',
            'en': 'New Task Available'
        },
        'message': {
            'ar': 'مهمة جديدة "{title}" متاحة في منطقتك مقابل {budget} أوقية.',
            'fr': 'Une nouvelle tâche "{title}" est disponible dans votre zone pour {budget} MRU.',
            'en': 'A new task "{title}" is available in your area for {budget} MRU.'
        }
    },
    'message_received': {
        'title': {
            'ar': 'رسالة جديدة مستلمة',
            'fr': 'Nouveau message reçu',
            'en': 'New Message Received'
        },
        'message': {
            'ar': '{sender_name} أرسل لك رسالة بخصوص "{title}".',
            'fr': '{sender_name} vous a envoyé un message concernant "{title}".',
            'en': '{sender_name} sent you a message regarding "{title}".'
        }
    },
    'service_reminder': {
        'title': {
            'ar': 'تذكير بالخدمة',
            'fr': 'Rappel de service',
            'en': 'Service Reminder'
        },
        'message': {
            'ar': 'خدمتك "{title}" مع {worker_name} مجدولة في {scheduled_time}. لا تنسى!',
            'fr': 'Votre service "{title}" avec {worker_name} est programmé pour {scheduled_time}. N\'oubliez pas!',
            'en': 'Your service "{title}" with {worker_name} is scheduled for {scheduled_time}. Don\'t forget!'
        }
    },
    'service_cancelled': {
        'title': {
            'ar': 'تم إلغاء الخدمة',
            'fr': 'Service annulé',
            'en': 'Service Cancelled'
        },
        'message': {
            'ar': '{worker_name} اضطر لإلغاء موعدك "{title}". سيتواصل معك لإعادة الجدولة.',
            'fr': '{worker_name} a dû annuler votre rendez-vous "{title}". Il vous contactera pour reprogrammer.',
            'en': '{worker_name} had to cancel your appointment "{title}". They will contact you to reschedule.'
        }
    }
}

# ========================================
# دالة الحصول على النص المترجم
# ========================================

def get_translated_notification(notification_type: str, user_language: str, **kwargs) -> Dict[str, str]:
    """
    الحصول على العنوان والرسالة بلغة المستخدم
    """
    translations = NOTIFICATION_TRANSLATIONS.get(notification_type, {})
    
    # اللغة الافتراضية: الفرنسية
    if user_language not in ['ar', 'fr', 'en']:
        user_language = 'fr'
    
    # الحصول على العنوان
    title_dict = translations.get('title', {})
    title = title_dict.get(user_language, title_dict.get('fr', 'Notification'))
    
    # الحصول على الرسالة
    message_dict = translations.get('message', {})
    message_template = message_dict.get(user_language, message_dict.get('fr', ''))
    
    # تطبيق المتغيرات على النص
    try:
        message = message_template.format(**kwargs)
    except KeyError:
        message = message_template
    
    return {
        'title': title,
        'message': message
    }

# ========================================
# دالة إنشاء وإرسال الإشعار
# ========================================

def create_and_send_notification(
    recipient_user,
    notification_type: str,
    title: str = None,
    message: str = None,
    related_task=None,
    related_application=None,
    send_firebase: bool = True,
    **format_kwargs
) -> Dict[str, Any]:
    """
    إنشاء إشعار في قاعدة البيانات وإرساله عبر Firebase
    مع دعم اللغات المتعددة
    """
    
    try:
        # 1. التحقق من إعدادات الإشعارات
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
        
        # 2. الحصول على لغة المستخدم
        user_language = getattr(recipient_user, 'preferred_language', 'fr')
        
        # 3. الحصول على النص المترجم
        translated = get_translated_notification(
            notification_type,
            user_language,
            **format_kwargs
        )
        
        # استخدام النص المترجم أو النص المُمرر
        final_title = title or translated['title']
        final_message = message or translated['message']
        
        # 4. إنشاء الإشعار في قاعدة البيانات
        notification = Notification.objects.create(
            recipient=recipient_user,
            notification_type=notification_type,
            title=final_title,
            message=final_message,
            related_task=related_task,
            related_application=related_application
        )
        
        logger.info(f"Database notification created: {notification.id} (lang: {user_language})")
        
        # 5. إرسال عبر Firebase
        firebase_result = None
        if send_firebase and firebase_service.is_available():
            data = {
                'notification_id': str(notification.id),
                'notification_type': notification_type,
                'user_role': recipient_user.role,
                'language': user_language,
                'timestamp': timezone.now().isoformat(),
            }
            
            if related_task:
                data.update({
                    'task_id': str(related_task.id),
                    'task_title': related_task.title[:50]
                })
            
            firebase_result = firebase_service.send_to_user(
                user=recipient_user,
                title=final_title,
                body=final_message,
                data=data
            )
            
            if firebase_result.get('success'):
                logger.info(f"Firebase notification sent (lang: {user_language})")
            else:
                logger.error(f"Firebase sending failed: {firebase_result.get('error')}")
        
        return {
            'success': True,
            'notification_id': notification.id,
            'firebase_sent': firebase_result.get('success', False) if firebase_result else False,
            'firebase_result': firebase_result,
            'language': user_language,
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
        related_task=task,
        title=task.title
    )

def notify_worker_applied(client_user, worker_user, task, application):
    """إشعار تقدم العامل للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='worker_applied',
        related_task=task,
        related_application=application,
        worker_name=worker_name,
        title=task.title
    )

def notify_application_accepted(worker_user, task, client_user):
    """إشعار قبول الطلب للعامل"""
    client_name = client_user.get_full_name() or client_user.phone
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='application_accepted',
        related_task=task,
        title=task.title,
        client_name=client_name
    )

# def notify_application_rejected(worker_user, task):
#     """إشعار رفض الطلب للعامل"""
#     return create_and_send_notification(
#         recipient_user=worker_user,
#         notification_type='application_rejected',
#         related_task=task,
#         title=task.title
#     )

# def notify_task_completed(client_user, worker_user, task):
#     """إشعار اكتمال المهمة للعميل"""
#     worker_name = worker_user.get_full_name() or worker_user.phone
#     return create_and_send_notification(
#         recipient_user=client_user,
#         notification_type='task_completed',
#         related_task=task,
#         worker_name=worker_name,
#         title=task.title
#     )

# def notify_work_started(client_user, worker_user, task):
#     """إشعار العميل ببدء العامل في العمل"""
#     worker_name = worker_user.get_full_name() or worker_user.phone
#     return create_and_send_notification(
#         recipient_user=client_user,
#         notification_type='work_started',
#         related_task=task,
#         worker_name=worker_name,
#         title=task.title
#     )

# def notify_payment_received(client_user, task, amount):
#     """إشعار استلام الدفع للعميل"""
#     return create_and_send_notification(
#         recipient_user=client_user,
#         notification_type='payment_received',
#         related_task=task,
#         amount=amount,
#         title=task.title
# #     )

# def notify_payment_sent(worker_user, task, amount):
#     """إشعار إرسال الدفع للعامل"""
#     return create_and_send_notification(
#         recipient_user=worker_user,
#         notification_type='payment_sent',
#         related_task=task,
#         amount=amount,
#         title=task.title
#     )

def notify_new_task_available(worker_user, task):
    """إشعار مهمة جديدة متاحة للعامل"""
    return create_and_send_notification(
        recipient_user=worker_user,
        notification_type='new_task_available',
        related_task=task,
        title=task.title,
        budget=task.budget
    )

def notify_message_received(recipient_user, sender_user, task, message_preview=""):
    """إشعار استلام رسالة"""
    sender_name = sender_user.get_full_name() or sender_user.phone
    return create_and_send_notification(
        recipient_user=recipient_user,
        notification_type='message_received',
        related_task=task,
        sender_name=sender_name,
        title=task.title if task else ""
    )

def notify_service_reminder(client_user, worker_user, task, scheduled_time):
    """إشعار تذكير الخدمة للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    time_str = scheduled_time.strftime('%d/%m/%Y à %H:%M')
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='service_reminder',
        related_task=task,
        title=task.title,
        worker_name=worker_name,
        scheduled_time=time_str
    )

def notify_service_cancelled(client_user, worker_user, task, reason=""):
    """إشعار إلغاء الخدمة للعميل"""
    worker_name = worker_user.get_full_name() or worker_user.phone
    return create_and_send_notification(
        recipient_user=client_user,
        notification_type='service_cancelled',
        related_task=task,
        title=task.title,
        worker_name=worker_name
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
            'firebase_sent': result.get('firebase_sent', False),
            'language': result.get('language', 'fr')
        })
    
    successful_notifications = len([r for r in results if r['success']])
    logger.info(f"Bulk notification sent to {successful_notifications}/{len(worker_users)} workers")
    
    return {
        'total_workers': len(worker_users),
        'successful_notifications': successful_notifications,
        'results': results
    }

def cleanup_old_notifications(days=90):
    """تنظيف الإشعارات القديمة"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
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