# ===============================================  
# users/upload_views.py
# APIs رفع الصور وإدارتها
# ===============================================

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.core.exceptions import ValidationError
from .image_utils import ImageProcessor
from .validators import validate_image_file, validate_image_content
import traceback

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_image(request):
    """
    رفع صورة البروفايل
    POST /api/users/upload-profile-image/
    
    Body: FormData
    - image: ملف الصورة (required)
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        # 1. التحقق من وجود الصورة
        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'لم يتم إرسال صورة',
                'code': 'NO_IMAGE_PROVIDED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['image']
        user = request.user
        
        # تسجيل معلومات للتتبع
        print(f"[DEBUG] User {user.id} uploading image: {uploaded_file.name}, Size: {uploaded_file.size} bytes")
        
        # 2. التحقق من صحة الصورة
        try:
            validate_image_file(uploaded_file)
            validate_image_content(uploaded_file)
        except ValidationError as ve:
            return Response({
                'success': False,
                'error': str(ve),
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. معالجة الصورة
        try:
            processed_images = ImageProcessor.process_profile_image(
                uploaded_file, user.id
            )
            print(f"[DEBUG] Image processing completed for user {user.id}")
        except ValueError as ve:
            return Response({
                'success': False,
                'error': str(ve),
                'code': 'IMAGE_PROCESSING_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. حفظ الصورة في البروفايل المناسب
        with transaction.atomic():
            try:
                # حذف الصور القديمة
                ImageProcessor.delete_old_images(user, user.role)
                
                # حفظ الصورة الجديدة حسب نوع المستخدم
                if user.role == 'client':
                    # إنشاء أو تحديث ملف العميل
                    from .models import ClientProfile
                    profile, created = ClientProfile.objects.get_or_create(user=user)
                    profile.profile_image = processed_images['full']
                    profile.save()
                    
                    image_url = request.build_absolute_uri(profile.profile_image.url)
                    print(f"[DEBUG] Client profile updated for user {user.id}")
                    
                elif user.role == 'worker':
                    # تحديث ملف العامل
                    if not hasattr(user, 'worker_profile'):
                        return Response({
                            'success': False,
                            'error': 'ملف العامل غير موجود',
                            'code': 'WORKER_PROFILE_NOT_FOUND'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    user.worker_profile.profile_image = processed_images['full']
                    user.worker_profile.save()
                    
                    image_url = request.build_absolute_uri(user.worker_profile.profile_image.url)
                    print(f"[DEBUG] Worker profile updated for user {user.id}")
                
                else:
                    return Response({
                        'success': False,
                        'error': f'نوع المستخدم غير مدعوم: {user.role}',
                        'code': 'UNSUPPORTED_USER_ROLE'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as db_error:
                print(f"[ERROR] Database error for user {user.id}: {str(db_error)}")
                return Response({
                    'success': False,
                    'error': 'خطأ في حفظ البيانات',
                    'code': 'DATABASE_ERROR'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 5. إرجاع الاستجابة الناجحة
        return Response({
            'success': True,
            'message': 'تم رفع صورة البروفايل بنجاح',
            'data': {
                'image_url': image_url,
                'user_id': user.id,
                'user_role': user.role,
                'uploaded_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # تسجيل الخطأ الكامل للمطورين
        print(f"[ERROR] Unexpected error in upload_profile_image: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        return Response({
            'success': False,
            'error': 'حدث خطأ غير متوقع أثناء رفع الصورة',
            'code': 'UNEXPECTED_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_profile_image(request):
    """
    حذف صورة البروفايل
    DELETE /api/users/delete-profile-image/
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        user = request.user
        print(f"[DEBUG] User {user.id} deleting profile image")
        
        with transaction.atomic():
            # حذف الصورة الفيزيائية
            ImageProcessor.delete_old_images(user, user.role)
            
            # إزالة رابط الصورة من قاعدة البيانات
            if user.role == 'client' and hasattr(user, 'client_profile'):
                user.client_profile.profile_image = None
                user.client_profile.save()
                
            elif user.role == 'worker' and hasattr(user, 'worker_profile'):
                user.worker_profile.profile_image = None
                user.worker_profile.save()
            
            else:
                return Response({
                    'success': False,
                    'error': 'لا توجد صورة للحذف',
                    'code': 'NO_IMAGE_TO_DELETE'
                }, status=status.HTTP_404_NOT_FOUND)
        
        print(f"[DEBUG] Profile image deleted for user {user.id}")
        
        return Response({
            'success': True,
            'message': 'تم حذف صورة البروفايل بنجاح',
            'data': {
                'user_id': user.id,
                'user_role': user.role
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Error deleting profile image for user {user.id}: {str(e)}")
        
        return Response({
            'success': False,
            'error': 'فشل في حذف صورة البروفايل',
            'code': 'DELETE_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_image(request):
    """
    الحصول على رابط صورة البروفايل
    GET /api/users/profile-image/
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        user = request.user
        image_url = None
        profile_exists = False
        
        # البحث عن الصورة حسب نوع المستخدم
        if user.role == 'client' and hasattr(user, 'client_profile'):
            profile_exists = True
            if user.client_profile.profile_image:
                image_url = request.build_absolute_uri(
                    user.client_profile.profile_image.url
                )
                
        elif user.role == 'worker' and hasattr(user, 'worker_profile'):
            profile_exists = True
            if user.worker_profile.profile_image:
                image_url = request.build_absolute_uri(
                    user.worker_profile.profile_image.url
                )
        
        return Response({
            'success': True,
            'data': {
                'image_url': image_url,
                'has_image': image_url is not None,
                'profile_exists': profile_exists,
                'user_id': user.id,
                'user_role': user.role
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Error getting profile image for user {user.id}: {str(e)}")
        
        return Response({
            'success': False,
            'error': 'فشل في جلب معلومات صورة البروفايل',
            'code': 'FETCH_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  
def get_image_upload_info(request):
    """
    الحصول على معلومات رفع الصور (للتطوير والاختبار)
    GET /api/users/image-upload-info/
    """
    
    return Response({
        'success': True,
        'data': {
            'max_size_mb': ImageProcessor.MAX_SIZE_MB,
            'allowed_formats': ImageProcessor.ALLOWED_FORMATS,
            'output_sizes': ImageProcessor.SIZES,
            'quality': ImageProcessor.QUALITY,
            'user_role': request.user.role,
            'user_id': request.user.id
        }
    }, status=status.HTTP_200_OK)