# ===============================================
# users/image_utils.py
# معالج الصور الاحترافي
# ===============================================

import os
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from io import BytesIO
import uuid
from django.conf import settings

class ImageProcessor:
    """معالج الصور الاحترافي"""
    
    # معايير الصور
    MAX_SIZE_MB = 5
    ALLOWED_FORMATS = ['JPEG', 'PNG', 'JPG']
    SIZES = {
        'thumbnail': (150, 150),
        'medium': (400, 400), 
        'full': (800, 800)
    }
    QUALITY = 85
    
    @classmethod
    def process_profile_image(cls, uploaded_file, user_id):
        """
        معالجة صورة البروفايل شاملة
        - التحقق من الصحة
        - القص المربع
        - إنشاء أحجام متعددة
        - الضغط
        """
        try:
            # 1. فحص الملف
            cls._validate_image(uploaded_file)
            
            # 2. فتح الصورة
            image = Image.open(uploaded_file)
            
            # 3. تصحيح الاتجاه (EXIF)
            image = ImageOps.exif_transpose(image)
            
            # 4. تحويل لـ RGB إذا لزم الأمر
            if image.mode in ('RGBA', 'LA', 'P'):
                # إنشاء خلفية بيضاء
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # 5. القص المربع (من المنتصف)
            image = cls._crop_square(image)
            
            # 6. إنشاء الأحجام المتعددة
            processed_images = {}
            for size_name, dimensions in cls.SIZES.items():
                processed_images[size_name] = cls._resize_and_compress(
                    image.copy(), dimensions, user_id, size_name
                )
            
            return processed_images
            
        except Exception as e:
            raise ValueError(f"خطأ في معالجة الصورة: {str(e)}")
    
    @classmethod
    def _validate_image(cls, uploaded_file):
        """التحقق من صحة الصورة"""
        
        # فحص الحجم
        if uploaded_file.size > cls.MAX_SIZE_MB * 1024 * 1024:
            raise ValueError(f"حجم الصورة كبير جداً. الحد الأقصى {cls.MAX_SIZE_MB}MB")
        
        # فحص النوع
        try:
            image = Image.open(uploaded_file)
            if image.format not in cls.ALLOWED_FORMATS:
                raise ValueError(f"نوع الصورة غير مدعوم. الأنواع المدعومة: {', '.join(cls.ALLOWED_FORMATS)}")
            
            # فحص أبعاد معقولة
            width, height = image.size
            if width < 100 or height < 100:
                raise ValueError("الصورة صغيرة جداً. الحد الأدنى 100x100 بكسل")
            
            if width > 4000 or height > 4000:
                raise ValueError("الصورة كبيرة جداً. الحد الأقصى 4000x4000 بكسل")
                
            uploaded_file.seek(0)  # إعادة تعيين مؤشر الملف
            
        except Exception as e:
            raise ValueError(f"ملف الصورة تالف أو غير صالح: {str(e)}")
    
    @classmethod
    def _crop_square(cls, image):
        """قص الصورة لشكل مربع من المنتصف"""
        width, height = image.size
        
        # تحديد أصغر بُعد
        min_dimension = min(width, height)
        
        # حساب نقطة البداية للقص من المنتصف
        left = (width - min_dimension) // 2
        top = (height - min_dimension) // 2
        right = left + min_dimension
        bottom = top + min_dimension
        
        # قص الصورة
        return image.crop((left, top, right, bottom))
    
    @classmethod
    def _resize_and_compress(cls, image, target_size, user_id, size_name):
        """تغيير الحجم والضغط"""
        
        # تغيير الحجم مع الحفاظ على الجودة
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # حفظ في memory
        output = BytesIO()
        image.save(output, format='JPEG', quality=cls.QUALITY, optimize=True)
        output.seek(0)
        
        # إنشاء اسم ملف فريد
        filename = f"profile_{user_id}_{size_name}_{uuid.uuid4().hex[:8]}.jpg"
        
        # تحويل لـ Django File
        django_file = ContentFile(
            output.getvalue(),
            name=filename
        )
        
        return django_file

    @classmethod
    def delete_old_images(cls, user, role):
        """حذف الصور القديمة"""
        try:
            if role == 'client':
                profile = getattr(user, 'client_profile', None)
                if profile and profile.profile_image:
                    # حذف الصورة الفيزيائية
                    if os.path.isfile(profile.profile_image.path):
                        os.remove(profile.profile_image.path)
            
            elif role == 'worker':
                profile = getattr(user, 'worker_profile', None)
                if profile and profile.profile_image:
                    if os.path.isfile(profile.profile_image.path):
                        os.remove(profile.profile_image.path)
                        
        except Exception as e:
            # تسجيل الخطأ لكن لا نفشل العملية
            print(f"خطأ في حذف الصورة القديمة: {str(e)}")

    @classmethod
    def create_default_avatar(cls, user_id, role):
        """إنشاء صورة افتراضية (اختياري)"""
        try:
            # إنشاء صورة بسيطة بلون خلفية
            image = Image.new('RGB', (800, 800), color=(200, 200, 200))
            
            # يمكن إضافة نص أو أيقونة هنا
            
            output = BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            filename = f"default_{role}_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
            
            return ContentFile(
                output.getvalue(),
                name=filename
            )
            
        except Exception as e:
            print(f"خطأ في إنشاء الصورة الافتراضية: {str(e)}")
            return None