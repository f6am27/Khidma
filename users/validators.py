# ===============================================
# users/validators.py
# التحقق من صحة الملفات والصور
# ===============================================

from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
import magic
import os

def validate_image_file(uploaded_file):
    """التحقق الشامل من ملف الصورة"""
    
    # 1. فحص الحجم
    max_size = 5 * 1024 * 1024  # 5MB
    if uploaded_file.size > max_size:
        raise ValidationError(f"حجم الصورة كبير جداً. الحد الأقصى 5MB")
    
    # 2. فحص نوع الملف الحقيقي (MIME type)
    try:
        uploaded_file.seek(0)
        file_mime = magic.from_buffer(uploaded_file.read(2048), mime=True)
        uploaded_file.seek(0)
    except Exception:
        # في حالة فشل python-magic، نستخدم طريقة بديلة
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        extension_to_mime = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png'
        }
        file_mime = extension_to_mime.get(file_extension, 'unknown')
    
    allowed_mimes = ['image/jpeg', 'image/png', 'image/jpg']
    if file_mime not in allowed_mimes:
        raise ValidationError("نوع الملف غير مدعوم. يُسمح فقط بـ JPEG و PNG")
    
    # 3. فحص أبعاد الصورة
    try:
        width, height = get_image_dimensions(uploaded_file)
        if not width or not height:
            raise ValidationError("لا يمكن قراءة أبعاد الصورة")
        
        if width < 100 or height < 100:
            raise ValidationError("الصورة صغيرة جداً. الحد الأدنى 100x100 بكسل")
        
        if width > 4000 or height > 4000:
            raise ValidationError("الصورة كبيرة جداً. الحد الأقصى 4000x4000 بكسل")
            
    except Exception as e:
        raise ValidationError(f"خطأ في قراءة بيانات الصورة: {str(e)}")
    
    # إعادة تعيين مؤشر الملف
    uploaded_file.seek(0)
    
    return True

def validate_file_name(filename):
    """التحقق من اسم الملف وتنظيفه"""
    
    # قائمة المحارف المحظورة
    forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    
    # إزالة المحارف المحظورة
    clean_name = filename
    for char in forbidden_chars:
        clean_name = clean_name.replace(char, '_')
    
    # التأكد من طول الاسم
    if len(clean_name) > 100:
        name, ext = os.path.splitext(clean_name)
        clean_name = name[:90] + ext
    
    return clean_name

def validate_image_content(uploaded_file):
    """فحص محتوى الصورة للتأكد من أنها صورة حقيقية"""
    
    try:
        from PIL import Image
        
        # محاولة فتح الصورة
        image = Image.open(uploaded_file)
        
        # التحقق من أن الصورة قابلة للقراءة
        image.verify()
        
        # إعادة تعيين مؤشر الملف
        uploaded_file.seek(0)
        
        return True
        
    except Exception as e:
        raise ValidationError(f"الملف ليس صورة صالحة: {str(e)}")

def validate_upload_path(file_path):
    """التحقق من مسار رفع الملف لتجنب Path Traversal"""
    
    # تحويل المسار لمسار مطلق
    abs_path = os.path.abspath(file_path)
    
    # التحقق من أن المسار داخل MEDIA_ROOT
    from django.conf import settings
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    
    if not abs_path.startswith(media_root):
        raise ValidationError("مسار الملف غير آمن")
    
    return True