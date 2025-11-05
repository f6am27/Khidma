# admin_api/upload_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.core.exceptions import ValidationError
from users.image_utils import ImageProcessor
from users.validators import validate_image_file, validate_image_content
from users.models import AdminProfile
import traceback


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_admin_profile_image(request):
    """
    رفع صورة البروفايل للأدمن
    POST /api/admin/upload-profile-image/
    
    Body: FormData
    - image: ملف الصورة (required)
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        # 1. التحقق من أن المستخدم أدمن
        if request.user.role != 'admin':
            return Response({
                'success': False,
                'error': 'هذه الخدمة متاحة للأدمن فقط',
                'code': 'NOT_ADMIN'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 2. التحقق من وجود الصورة
        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'لم يتم إرسال صورة',
                'code': 'NO_IMAGE_PROVIDED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['image']
        user = request.user
        
        print(f"[DEBUG] Admin {user.id} uploading image: {uploaded_file.name}, Size: {uploaded_file.size} bytes")
        
        # 3. التحقق من صحة الصورة
        try:
            validate_image_file(uploaded_file)
            validate_image_content(uploaded_file)
        except ValidationError as ve:
            return Response({
                'success': False,
                'error': str(ve),
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. معالجة الصورة
        try:
            processed_images = ImageProcessor.process_profile_image(
                uploaded_file, user.id
            )
            print(f"[DEBUG] Image processing completed for admin {user.id}")
        except ValueError as ve:
            return Response({
                'success': False,
                'error': str(ve),
                'code': 'IMAGE_PROCESSING_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 5. حفظ الصورة في AdminProfile
        with transaction.atomic():
            try:
                # حذف الصورة القديمة
                ImageProcessor.delete_old_images(user, 'admin')
                
                # إنشاء أو تحديث AdminProfile
                profile, created = AdminProfile.objects.get_or_create(user=user)
                profile.profile_image = processed_images['full']
                profile.save()
                
                image_url = request.build_absolute_uri(profile.profile_image.url)
                print(f"[DEBUG] Admin profile updated for user {user.id}")
                
            except Exception as db_error:
                print(f"[ERROR] Database error for admin {user.id}: {str(db_error)}")
                return Response({
                    'success': False,
                    'error': 'خطأ في حفظ البيانات',
                    'code': 'DATABASE_ERROR'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 6. إرجاع الاستجابة الناجحة
        return Response({
            'success': True,
            'message': 'تم رفع صورة البروفايل بنجاح',
            'data': {
                'image_url': image_url,
                'user_id': user.id,
                'user_role': user.role,
                'uploaded_at': profile.updated_at.isoformat() if hasattr(profile, 'updated_at') else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Unexpected error in upload_admin_profile_image: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        return Response({
            'success': False,
            'error': 'حدث خطأ غير متوقع أثناء رفع الصورة',
            'code': 'UNEXPECTED_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_admin_profile_image(request):
    """
    حذف صورة البروفايل للأدمن
    DELETE /api/admin/delete-profile-image/
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        user = request.user
        
        # التحقق من أن المستخدم أدمن
        if user.role != 'admin':
            return Response({
                'success': False,
                'error': 'هذه الخدمة متاحة للأدمن فقط',
                'code': 'NOT_ADMIN'
            }, status=status.HTTP_403_FORBIDDEN)
        
        print(f"[DEBUG] Admin {user.id} deleting profile image")
        
        with transaction.atomic():
            # حذف الصورة الفيزيائية
            ImageProcessor.delete_old_images(user, 'admin')
            
            # إزالة رابط الصورة من قاعدة البيانات
            if hasattr(user, 'admin_profile') and user.admin_profile:
                user.admin_profile.profile_image = None
                user.admin_profile.save()
            else:
                return Response({
                    'success': False,
                    'error': 'لا توجد صورة للحذف',
                    'code': 'NO_IMAGE_TO_DELETE'
                }, status=status.HTTP_404_NOT_FOUND)
        
        print(f"[DEBUG] Profile image deleted for admin {user.id}")
        
        return Response({
            'success': True,
            'message': 'تم حذف صورة البروفايل بنجاح',
            'data': {
                'user_id': user.id,
                'user_role': user.role
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[ERROR] Error deleting profile image for admin {user.id}: {str(e)}")
        
        return Response({
            'success': False,
            'error': 'فشل في حذف صورة البروفايل',
            'code': 'DELETE_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_profile_image(request):
    """
    الحصول على رابط صورة البروفايل للأدمن
    GET /api/admin/profile-image/
    
    Headers:
    - Authorization: Bearer <token>
    """
    
    try:
        user = request.user
        
        # التحقق من أن المستخدم أدمن
        if user.role != 'admin':
            return Response({
                'success': False,
                'error': 'هذه الخدمة متاحة للأدمن فقط',
                'code': 'NOT_ADMIN'
            }, status=status.HTTP_403_FORBIDDEN)
        
        image_url = None
        profile_exists = False
        
        # البحث عن الصورة
        if hasattr(user, 'admin_profile') and user.admin_profile:
            profile_exists = True
            if user.admin_profile.profile_image:
                image_url = request.build_absolute_uri(
                    user.admin_profile.profile_image.url
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
        print(f"[ERROR] Error getting profile image for admin {user.id}: {str(e)}")
        
        return Response({
            'success': False,
            'error': 'فشل في جلب معلومات صورة البروفايل',
            'code': 'FETCH_FAILED'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)