# notifications/device_views.py
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import IntegrityError
from .models import DeviceToken, Notification
from .firebase_service import firebase_service
import logging
from django.utils import timezone

logger = logging.getLogger('firebase_notifications')

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def register_device_token(request):
    """
    تسجيل رمز جهاز جديد
    Register new device token
    
    POST /api/notifications/register-device/
    Body: {
        "token": "firebase_token_here",
        "platform": "android|ios|web",
        "device_name": "Samsung Galaxy S21",
        "app_version": "1.0.0"
    }
    """
    try:
        user = request.user
        token = request.data.get('token')
        platform = request.data.get('platform', 'android')
        device_name = request.data.get('device_name', '')
        app_version = request.data.get('app_version', '')
        
        # التحقق من وجود الرمز
        if not token:
            return Response({
                'success': False,
                'error': 'Device token is required',
                'code': 'TOKEN_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # التحقق من صحة المنصة
        valid_platforms = ['android', 'ios', 'web']
        if platform not in valid_platforms:
            return Response({
                'success': False,
                'error': f'Invalid platform. Must be one of: {valid_platforms}',
                'code': 'INVALID_PLATFORM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # محاولة إنشاء أو تحديث الرمز
        device_token, created = DeviceToken.objects.get_or_create(
            token=token,
            defaults={
                'user': user,
                'platform': platform,
                'device_name': device_name,
                'app_version': app_version,
                'is_active': True,
                'notifications_enabled': True
            }
        )
        
        # إذا كان الرمز موجود لمستخدم آخر، حدث المالك
        if not created and device_token.user != user:
            device_token.user = user
            device_token.platform = platform
            device_token.device_name = device_name
            device_token.app_version = app_version
            device_token.is_active = True
            device_token.save()
        
        # إذا كان للمستخدم نفسه، حدث المعلومات
        elif not created:
            device_token.platform = platform
            device_token.device_name = device_name
            device_token.app_version = app_version
            device_token.is_active = True
            device_token.notifications_enabled = True
            device_token.save()
        
        # تحديث آخر استخدام
        device_token.update_last_used()
        
        logger.info(f"Device token {'registered' if created else 'updated'} for user {user.phone}")
        
        return Response({
            'success': True,
            'message': 'Device token registered successfully',
            'data': {
                'device_id': device_token.id,
                'platform': device_token.platform,
                'device_name': device_token.device_name,
                'created': created,
                'user_id': user.id,
                'user_role': user.role
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except IntegrityError as e:
        logger.error(f"Database error registering device token: {str(e)}")
        return Response({
            'success': False,
            'error': 'Database error occurred',
            'code': 'DATABASE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Unexpected error registering device token: {str(e)}")
        return Response({
            'success': False,
            'error': 'Unexpected error occurred',
            'code': 'UNEXPECTED_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_device_settings(request, device_id):
    """
    تحديث إعدادات الجهاز
    Update device settings
    
    PUT /api/notifications/device/<device_id>/settings/
    Body: {
        "notifications_enabled": true|false,
        "device_name": "New device name"
    }
    """
    try:
        user = request.user
        
        # البحث عن الجهاز
        try:
            device_token = DeviceToken.objects.get(id=device_id, user=user)
        except DeviceToken.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Device not found',
                'code': 'DEVICE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # تحديث الإعدادات
        notifications_enabled = request.data.get('notifications_enabled')
        device_name = request.data.get('device_name')
        
        updated_fields = []
        
        if notifications_enabled is not None:
            device_token.notifications_enabled = notifications_enabled
            updated_fields.append('notifications_enabled')
        
        if device_name:
            device_token.device_name = device_name
            updated_fields.append('device_name')
        
        if updated_fields:
            device_token.save(update_fields=updated_fields + ['updated_at'])
        
        return Response({
            'success': True,
            'message': 'Device settings updated successfully',
            'data': {
                'device_id': device_token.id,
                'notifications_enabled': device_token.notifications_enabled,
                'device_name': device_token.device_name,
                'updated_fields': updated_fields
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating device settings: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to update device settings',
            'code': 'UPDATE_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def unregister_device_token(request, device_id):
    """
    إلغاء تسجيل جهاز
    Unregister device token
    
    DELETE /api/notifications/device/<device_id>/
    """
    try:
        user = request.user
        
        # البحث عن الجهاز وحذفه
        deleted_count = DeviceToken.objects.filter(
            id=device_id, 
            user=user
        ).delete()[0]
        
        if deleted_count == 0:
            return Response({
                'success': False,
                'error': 'Device not found',
                'code': 'DEVICE_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        logger.info(f"Device token {device_id} unregistered for user {user.phone}")
        
        return Response({
            'success': True,
            'message': 'Device unregistered successfully',
            'data': {
                'device_id': device_id,
                'user_id': user.id
            }
        })
        
    except Exception as e:
        logger.error(f"Error unregistering device: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to unregister device',
            'code': 'UNREGISTER_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_user_devices(request):
    """
    قائمة أجهزة المستخدم
    List user devices
    
    GET /api/notifications/devices/
    """
    try:
        user = request.user
        
        devices = DeviceToken.objects.filter(user=user).order_by('-last_used')
        
        devices_data = []
        for device in devices:
            devices_data.append({
                'id': device.id,
                'platform': device.platform,
                'device_name': device.device_name or f'{device.platform.capitalize()} Device',
                'app_version': device.app_version,
                'is_active': device.is_active,
                'notifications_enabled': device.notifications_enabled,
                'total_notifications_sent': device.total_notifications_sent,
                'last_used': device.last_used.isoformat() if device.last_used else None,
                'created_at': device.created_at.isoformat(),
                'is_fresh': device.is_fresh
            })
        
        return Response({
            'success': True,
            'data': {
                'devices': devices_data,
                'total_devices': len(devices_data),
                'active_devices': len([d for d in devices_data if d['is_active']]),
                'user_id': user.id,
                'user_role': user.role
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing user devices: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve devices',
            'code': 'RETRIEVE_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_notification(request):
    """
    اختبار إرسال إشعار
    Test sending notification
    
    POST /api/notifications/test/
    Body: {
        "title": "Test notification",
        "message": "This is a test message"
    }
    """
    try:
        user = request.user
        title = request.data.get('title', 'Test Notification')
        message = request.data.get('message', 'This is a test notification from your app.')
        
        # التحقق من توفر Firebase
        if not firebase_service.is_available():
            return Response({
                'success': False,
                'error': 'Firebase service not available',
                'code': 'FIREBASE_UNAVAILABLE'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # إرسال إشعار اختباري
        result = firebase_service.send_to_user(
            user=user,
            title=title,
            body=message,
            data={
                'type': 'test',
                'timestamp': str(timezone.now()),
                'user_id': str(user.id)
            }
        )
        
        # إنشاء إشعار في قاعدة البيانات للاختبار
        notification = Notification.objects.create(
            recipient=user,
            notification_type='message_received',  # نوع عام للاختبار
            title=title,
            message=message
        )
        
        return Response({
            'success': True,
            'message': 'Test notification sent',
            'data': {
                'firebase_result': result,
                'notification_id': notification.id,
                'title': title,
                'message': message,
                'sent_to_devices': result.get('success_count', 0) if result.get('success') else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to send test notification',
            'code': 'TEST_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)