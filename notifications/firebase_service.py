# notifications/firebase_service.py
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from django.db import models
from django.utils import timezone
from typing import List, Optional, Dict, Any
from .models import DeviceToken, NotificationLog

logger = logging.getLogger('firebase_notifications')

class FirebaseNotificationService:
    """
    خدمة إرسال الإشعارات عبر Firebase
    Firebase push notification service
    """
    
    _app = None
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """تهيئة Firebase Admin SDK"""
        if cls._initialized:
            return True
            
        try:
            # التحقق من وجود ملف الأوراق الاعتمادية
            if not settings.FIREBASE_CREDENTIALS_PATH.exists():
                logger.error(f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}")
                return False
            
            # تهيئة Firebase
            cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
            cls._app = firebase_admin.initialize_app(cred, {
                'projectId': settings.FIREBASE_PROJECT_ID,
            })
            
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            return False
    
    @classmethod
    def is_available(cls):
        """التحقق من إتاحة خدمة Firebase"""
        if not cls._initialized:
            return cls.initialize()
        return cls._initialized
    
    @classmethod
    def send_to_token(cls, token: str, title: str, body: str, data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        إرسال إشعار لجهاز واحد
        Send notification to a single device
        """
        if not cls.is_available():
            return {'success': False, 'error': 'Firebase not available'}
        
        try:
            # إعداد رسالة الإشعار
            notification = messaging.Notification(
                title=title,
                body=body
            )
            
            # إعدادات Android
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound=settings.FIREBASE_NOTIFICATIONS.get('DEFAULT_SOUND', 'default'),
                    channel_id='default_channel'
                )
            )
            
            # إعدادات iOS
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=settings.FIREBASE_NOTIFICATIONS.get('DEFAULT_SOUND', 'default'),
                        badge=1
                    )
                )
            )
            
            # إنشاء الرسالة
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token,
                android=android_config,
                apns=apns_config
            )
            
            # إرسال الرسالة
            response = messaging.send(message)
            
            logger.info(f"Notification sent successfully: {response}")
            
            return {
                'success': True,
                'message_id': response,
                'token': token
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to send notification to {token}: {error_message}")
            
            # تحديد نوع الخطأ
            if 'not-found' in error_message.lower() or 'unregistered' in error_message.lower():
                return {'success': False, 'error': 'Invalid token', 'token': token}
            elif 'invalid-argument' in error_message.lower():
                return {'success': False, 'error': 'Invalid argument', 'token': token}
            else:
                return {'success': False, 'error': error_message, 'token': token}
    
    @classmethod
    def send_to_multiple_tokens(cls, tokens: List[str], title: str, body: str, data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        إرسال إشعار لعدة أجهزة
        Send notification to multiple devices
        """
        if not cls.is_available():
            return {'success': False, 'error': 'Firebase not available'}
        
        if not tokens:
            return {'success': True, 'successful_tokens': [], 'failed_tokens': []}
        
        try:
            # إعداد رسالة الإشعار
            notification = messaging.Notification(
                title=title,
                body=body
            )
            
            # إعدادات Android
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound=settings.FIREBASE_NOTIFICATIONS.get('DEFAULT_SOUND', 'default'),
                    channel_id='default_channel'
                )
            )
            
            # إعدادات iOS
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=settings.FIREBASE_NOTIFICATIONS.get('DEFAULT_SOUND', 'default'),
                        badge=1
                    )
                )
            )
            
            # ✅ إنشاء رسائل منفصلة لكل token (بدلاً من multicast)
            messages = []
            for token in tokens:
                message = messaging.Message(
                    notification=notification,
                    data=data or {},
                    token=token,
                    android=android_config,
                    apns=apns_config
                )
                messages.append(message)
            
            # ✅ إرسال جميع الرسائل دفعة واحدة (FCM v1 compatible)
            response = messaging.send_each(messages)
            
            # تحليل النتائج
            successful_tokens = []
            failed_tokens = []
            
            for i, result in enumerate(response.responses):
                token = tokens[i]
                if result.success:
                    successful_tokens.append(token)
                else:
                    error_code = 'Unknown error'
                    if result.exception:
                        error_message = str(result.exception)
                        if 'not-found' in error_message.lower() or 'unregistered' in error_message.lower():
                            error_code = 'UNREGISTERED'
                        elif 'invalid-argument' in error_message.lower():
                            error_code = 'INVALID_ARGUMENT'
                        else:
                            error_code = error_message
                    
                    failed_tokens.append({
                        'token': token,
                        'error': error_code
                    })
            
            logger.info(f"Batch sent: {response.success_count}/{len(tokens)} successful")
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'successful_tokens': successful_tokens,
                'failed_tokens': failed_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to send batch notification: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def send_to_user(cls, user, title: str, body: str, data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        إرسال إشعار لجميع أجهزة المستخدم
        Send notification to all user devices
        """
        try:
            # الحصول على رموز الأجهزة النشطة
            tokens = list(DeviceToken.get_user_active_tokens(user))
            
            if not tokens:
                logger.warning(f"No active tokens found for user {user.phone}")
                return {'success': True, 'message': 'No active devices'}
            
            # إرسال للأجهزة المتعددة
            result = cls.send_to_multiple_tokens(tokens, title, body, data)
            
            # تحديث إحصائيات الأجهزة
            if result['success'] and 'successful_tokens' in result:
                DeviceToken.objects.filter(
                    token__in=result['successful_tokens']
                ).update(
                    total_notifications_sent=models.F('total_notifications_sent') + 1,
                    last_notification_sent=timezone.now()
                )
            
            # إلغاء تفعيل الرموز غير الصالحة
            if result['success'] and 'failed_tokens' in result:
                invalid_tokens = [
                    ft['token'] for ft in result['failed_tokens'] 
                    if ft.get('error') in ['UNREGISTERED', 'INVALID_ARGUMENT']
                ]
                if invalid_tokens:
                    DeviceToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
                    logger.info(f"Deactivated {len(invalid_tokens)} invalid tokens")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {user.phone}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def log_notification_result(cls, notification, device_token, result: Dict[str, Any]):
        """
        تسجيل نتيجة إرسال الإشعار
        Log notification sending result
        """
        try:
            log_entry = NotificationLog.objects.create(
                notification=notification,
                device_token=device_token,
                status='sent' if result['success'] else 'failed',
                firebase_message_id=result.get('message_id', ''),
                error_message=result.get('error', '')
            )
            
            if result['success']:
                log_entry.mark_as_sent(result.get('message_id'))
                device_token.increment_notification_count()
            else:
                log_entry.mark_as_failed(result.get('error', 'Unknown error'))
                
                # إلغاء تفعيل الجهاز بعد عدة فشل متتالي
                if result.get('error') == 'Invalid token':
                    device_token.deactivate()
            
        except Exception as e:
            logger.error(f"Failed to log notification result: {str(e)}")
    
    @classmethod
    def cleanup_invalid_tokens(cls):
        """
        تنظيف الرموز غير الصالحة
        Clean up invalid tokens
        """
        try:
            # إلغاء تفعيل الرموز القديمة
            old_count = DeviceToken.cleanup_old_tokens(days=60)
            
            # إلغاء تفعيل الرموز التي فشل إرسالها مراراً
            failed_tokens = DeviceToken.objects.filter(
                firebase_logs__status='failed',
                firebase_logs__retry_count__gte=3
            ).distinct()
            
            failed_count = failed_tokens.count()
            failed_tokens.update(is_active=False)
            
            logger.info(f"Cleanup: {old_count} old tokens, {failed_count} failed tokens")
            
            return {
                'old_tokens_removed': old_count,
                'failed_tokens_deactivated': failed_count
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup tokens: {str(e)}")
            return {'error': str(e)}


# تهيئة الخدمة عند استيراد الملف
firebase_service = FirebaseNotificationService()