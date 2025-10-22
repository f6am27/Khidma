# workers/serializers.py - النسخة المحدثة مع حقول الموقع
from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import WorkerService, WorkerGallery, WorkerSettings
from users.models import User
from services.serializers import ServiceCategorySerializer


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user info for worker display
    معلومات المستخدم الأساسية لعرض العامل
    """
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone', 'date_joined']


class WorkerServiceSerializer(serializers.ModelSerializer):
    """
    Worker services with pricing
    خدمات العامل مع الأسعار
    """
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = WorkerService
        fields = [
            'id', 'category', 'category_id', 'base_price', 'price_type',
            'description', 'is_active', 'min_duration_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkerGallerySerializer(serializers.ModelSerializer):
    """
    Worker gallery/portfolio images
    معرض أعمال العامل
    """
    service_category = ServiceCategorySerializer(read_only=True)
    
    class Meta:
        model = WorkerGallery
        fields = [
            'id', 'image', 'caption', 'service_category', 
            'is_featured', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkerSettingsSerializer(serializers.ModelSerializer):
    """
    Worker settings serializer with partial update support
    محول إعدادات العامل مع دعم التحديث الجزئي
    """
    class Meta:
        model = WorkerSettings
        fields = [
            'push_notifications', 'email_notifications', 'sms_notifications',
            'theme_preference', 'language', 'auto_accept_jobs', 'max_daily_jobs',
            'profile_visibility', 'travel_radius_km', 'instant_booking'
        ]
    
    def __init__(self, *args, **kwargs):
        """Initialize with partial update support"""
        super().__init__(*args, **kwargs)
        self.partial = True
        for field_name, field in self.fields.items():
            field.required = False


# ============================
# إضافات الموقع الجديدة
# ============================

# Serializer جديد لإدارة الموقع
class WorkerLocationSerializer(serializers.Serializer):
    """
    Serializer لتفعيل/إيقاف وتحديث موقع العامل
    """
    location_sharing_enabled = serializers.BooleanField(read_only=True)
    current_latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    current_longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    location_accuracy = serializers.FloatField(required=False, allow_null=True)
    location_last_updated = serializers.DateTimeField(read_only=True)
    location_status = serializers.CharField(read_only=True)
    
    def validate(self, data):
        latitude = data.get('current_latitude')
        longitude = data.get('current_longitude')
        
        if (latitude is not None and longitude is None) or (longitude is not None and latitude is None):
            raise serializers.ValidationError(
                "يجب تقديم خط العرض والطول معًا"
            )
        
        if latitude is not None and not (-90 <= float(latitude) <= 90):
            raise serializers.ValidationError("خط العرض يجب أن يكون بين -90 و 90")
        if longitude is not None and not (-180 <= float(longitude) <= 180):
            raise serializers.ValidationError("خط الطول يجب أن يكون بين -180 و 180")
        
        return data


class LocationToggleSerializer(serializers.Serializer):
    """
    Serializer لتفعيل/إيقاف مشاركة الموقع
    """
    enabled = serializers.BooleanField(required=True)
    
    def validate_enabled(self, value):
        if not isinstance(value, bool):
            raise serializers.ValidationError("القيمة يجب أن تكون true أو false")
        return value


# ============================
# تحديث WorkerProfileListSerializer
# ============================

class WorkerProfileListSerializer(serializers.ModelSerializer):
    """
    Flutter-compatible serializer for worker list/search
    مع معلومات الموقع والخدمة
    """
    name = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField() 
    category = serializers.SerializerMethodField()  # ✅ نوع الخدمة من WorkerProfile
    rating = serializers.SerializerMethodField()
    minPrice = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    phone = serializers.CharField(read_only=True)
    distance = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    isFavorite = serializers.SerializerMethodField()
    
    user = UserBasicSerializer(read_only=True)
    services = serializers.SerializerMethodField()
    
    # حقول الموقع الجديدة
    location_sharing_enabled = serializers.SerializerMethodField()
    current_location_available = serializers.SerializerMethodField()
    distance_from_client = serializers.SerializerMethodField()
    location_last_updated = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'name', 'service', 'category', 'rating', 'distance', 'time', 
            'price', 'minPrice', 'image', 'isFavorite', 'area', 'phone',
            'id', 'user', 'services',
            'location_sharing_enabled',
            'current_location_available', 
            'distance_from_client',
            'location_last_updated'
        ]
    
    def get_location_sharing_enabled(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.location_sharing_enabled
        return False
    
    def get_current_location_available(self, obj):
        if hasattr(obj, 'worker_profile'):
            profile = obj.worker_profile
            return (
                profile.location_sharing_enabled and 
                profile.location_status == 'active' and
                profile.is_location_fresh()
            )
        return False
    
    def get_distance_from_client(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(obj, 'worker_profile'):
            return None
        client_lat = request.query_params.get('lat')
        client_lng = request.query_params.get('lng')
        if not (client_lat and client_lng):
            return None
        try:
            client_lat = float(client_lat)
            client_lng = float(client_lng)
            profile = obj.worker_profile
            if (profile.current_latitude and profile.current_longitude and 
                profile.location_sharing_enabled and profile.location_status == 'active'):
                distance_km = profile.calculate_distance_to(client_lat, client_lng)
                return round(distance_km, 1) if distance_km else None
        except (ValueError, TypeError):
            pass
        return None
    
    def get_location_last_updated(self, obj):
        if hasattr(obj, 'worker_profile') and obj.worker_profile.location_last_updated:
            return obj.worker_profile.location_last_updated
        return None
    
    def get_distance(self, obj):
        real_distance = self.get_distance_from_client(obj)
        if real_distance is not None:
            return f"{real_distance} km"
        import random
        return f"{random.uniform(0.5, 5.0):.1f} km"
    
    def get_name(self, obj):
        """احصل على الاسم الكامل للعامل"""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.phone or "Worker"

    def get_service(self, obj):
        """احصل على نوع الخدمة"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_category or "Service"
        return "Service"

    def get_category(self, obj):
        """✅ احصل على فئة الخدمة من WorkerProfile"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_category or "Service"
        return "Service"

    def get_area(self, obj):
        """احصل على منطقة الخدمة"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_area or "Zone"
        return "Zone"

    def get_phone(self, obj):
        """احصل على الهاتف"""
        return obj.phone or ""

    def get_image(self, obj):
        """✅ احصل على صورة البروفايل مع URL الكامل"""
        request = self.context.get('request')
        if hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            image_url = obj.worker_profile.profile_image.url
            # إذا كان لدينا request، اجعل URL مطلق
            if request:
                return request.build_absolute_uri(image_url)
            return image_url
        return None

    def get_rating(self, obj):
        """احصل على التقييم"""
        if hasattr(obj, 'worker_profile'):
            return float(obj.worker_profile.average_rating) or 0.0
        return 0.0

    def get_reviewCount(self, obj):
        """احصل على عدد التقييمات"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.total_reviews
        return 0

    def get_completedJobs(self, obj):
        """احصل على عدد المهام المنجزة"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.total_jobs_completed
        return 0

    def get_isOnline(self, obj):
        """احصل على حالة الاتصال"""
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.is_online
        return False

    def get_time(self, obj):
        """احصل على الوقت المتوقع"""
        return "15 Min"

    def get_price(self, obj):
        """✅ لا تعرض السعر - سيتم حذفه"""
        return None

    def get_minPrice(self, obj):
        """احصل على أقل سعر"""
        if hasattr(obj, 'worker_services') and obj.worker_services.exists():
            return float(obj.worker_services.first().base_price) or 0.0
        return 0.0



    def get_isFavorite(self, obj):
        """تحقق من حالة المفضلة"""
        request = self.context.get('request')
        
        # التحقق من وجود user مسجل الدخول
        if request and request.user and request.user.is_authenticated and request.user.role == 'client':
            from clients.models import FavoriteWorker
            is_favorite = FavoriteWorker.objects.filter(
                client=request.user,
                worker=obj
            ).exists()
            return is_favorite
        
        # في حالة عدم وجود user أو لم يكن مسجل دخول
        return False

    def get_services(self, obj):
        """احصل على قائمة الخدمات"""
        if hasattr(obj, 'worker_services') and obj.worker_services.exists():
            return [service.category.name for service in obj.worker_services.filter(is_active=True)]
        return []
# ============================
# تحديث WorkerProfileSerializer
# ============================

class WorkerProfileSerializer(serializers.ModelSerializer):
    """
    Worker profile serializer for worker to view/edit their own profile
    مع معلومات الموقع
    """
    phone = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    bio = serializers.SerializerMethodField()
    service_area = serializers.SerializerMethodField()
    service_category = serializers.SerializerMethodField()
    base_price = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    available_days = serializers.SerializerMethodField()
    work_start_time = serializers.SerializerMethodField()
    work_end_time = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    total_jobs_completed = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    full_name = serializers.SerializerMethodField()
    member_since = serializers.SerializerMethodField()
    
    # حقول الموقع الجديدة
    location_sharing_enabled = serializers.SerializerMethodField()
    current_latitude = serializers.SerializerMethodField()
    current_longitude = serializers.SerializerMethodField()
    location_last_updated = serializers.SerializerMethodField()
    location_status = serializers.SerializerMethodField()
    location_accuracy = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'bio', 'service_area', 'service_category', 'base_price',
            'profile_image_url', 'available_days', 'work_start_time', 'work_end_time',
            'latitude', 'longitude', 'total_jobs_completed', 'average_rating',
            'total_reviews', 'is_verified', 'is_available', 'is_online',
            'member_since', 'created_at', 'updated_at',
            'location_sharing_enabled',
            'current_latitude',
            'current_longitude', 
            'location_last_updated',
            'location_status',
            'location_accuracy'
        ]
    
    def get_location_sharing_enabled(self, obj):
        return obj.worker_profile.location_sharing_enabled if hasattr(obj, 'worker_profile') else False
    
    def get_current_latitude(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.current_latitude
        return None
    
    def get_current_longitude(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.current_longitude  
        return None
    
    def get_location_last_updated(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.location_last_updated
        return None
    
    def get_location_status(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.location_status
        return 'disabled'
    
    def get_location_accuracy(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.location_accuracy
        return None
    
    def get_profile_image_url(self, obj):
        """احصل على صورة البروفايل مع URL الكامل"""
        if hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            request = self.context.get('request')
            image_url = obj.worker_profile.profile_image.url
            
            # طباعة للـ debugging
            print(f'📸 Worker {obj.id} image URL: {image_url}')
            
            # إذا كان لدينا request، اجعل URL مطلق
            if request:
                absolute_url = request.build_absolute_uri(image_url)
                print(f'✅ Absolute URL: {absolute_url}')
                return absolute_url
            
            # إرجاع URL النسبي
            print(f'⚠️ No request context, returning relative URL')
            return image_url
        
        print(f'❌ No profile image for worker {obj.id}')
        return None
    
    def get_bio(self, obj):
        return obj.worker_profile.bio if hasattr(obj, 'worker_profile') else ""

    def get_service_area(self, obj):
        return obj.worker_profile.service_area if hasattr(obj, 'worker_profile') else ""

    def get_service_category(self, obj):
        return obj.worker_profile.service_category if hasattr(obj, 'worker_profile') else ""

    def get_base_price(self, obj):
        if hasattr(obj, 'worker_profile'):
            return float(obj.worker_profile.base_price)
        return 0.0

    def get_available_days(self, obj):
        return obj.worker_profile.available_days if hasattr(obj, 'worker_profile') else []

    def get_work_start_time(self, obj):
        return str(obj.worker_profile.work_start_time) if hasattr(obj, 'worker_profile') else None

    def get_work_end_time(self, obj):
        return str(obj.worker_profile.work_end_time) if hasattr(obj, 'worker_profile') else None

    def get_latitude(self, obj):
        return obj.worker_profile.latitude if hasattr(obj, 'worker_profile') else None

    def get_longitude(self, obj):
        return obj.worker_profile.longitude if hasattr(obj, 'worker_profile') else None

    def get_total_jobs_completed(self, obj):
        return obj.worker_profile.total_jobs_completed if hasattr(obj, 'worker_profile') else 0

    def get_average_rating(self, obj):
        if hasattr(obj, 'worker_profile'):
            return float(obj.worker_profile.average_rating)
        return 0.0

    def get_total_reviews(self, obj):
        return obj.worker_profile.total_reviews if hasattr(obj, 'worker_profile') else 0

    def get_is_verified(self, obj):
        return obj.worker_profile.is_verified if hasattr(obj, 'worker_profile') else False

    def get_is_available(self, obj):
        return obj.worker_profile.is_available if hasattr(obj, 'worker_profile') else False

    def get_is_online(self, obj):
        return obj.worker_profile.is_online if hasattr(obj, 'worker_profile') else False

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone

    def get_member_since(self, obj):
        return obj.date_joined.strftime("%B %Y")


class WorkerProfileDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for worker profile view (for clients)
    محول مفصل لعرض ملف العامل (للعملاء)
    """
    user = UserBasicSerializer(read_only=True)
    phone = serializers.CharField(read_only=True)
    services = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    
    # Worker profile data
    bio = serializers.SerializerMethodField()
    service_area = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    available_days = serializers.SerializerMethodField()
    work_start_time = serializers.SerializerMethodField()
    work_end_time = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    total_jobs_completed = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()
    
    # Computed fields
    completion_rate = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'user', 'phone', 'bio', 'service_area', 'profile_image',
            'available_days', 'work_start_time', 'work_end_time',
            'latitude', 'longitude', 'total_jobs_completed', 'average_rating', 
            'total_reviews', 'is_verified', 'is_available', 'is_online', 'last_seen',
            'services', 'gallery', 'completion_rate', 'response_time'
        ]
    
    def get_services(self, obj):
        if hasattr(obj, 'worker_services'):
            return WorkerServiceSerializer(obj.worker_services.filter(is_active=True), many=True).data
        return []
    
    def get_gallery(self, obj):
        if hasattr(obj, 'worker_gallery'):
            return WorkerGallerySerializer(obj.worker_gallery.all(), many=True).data
        return []
    
    # Worker profile field getters
    def get_bio(self, obj):
        return obj.worker_profile.bio if hasattr(obj, 'worker_profile') else ""
    
    def get_service_area(self, obj):
        return obj.worker_profile.service_area if hasattr(obj, 'worker_profile') else ""
    
    def get_profile_image(self, obj):
        if hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker_profile.profile_image.url)
            return obj.worker_profile.profile_image.url
        return None
    
    def get_available_days(self, obj):
        return obj.worker_profile.available_days if hasattr(obj, 'worker_profile') else []
    
    def get_work_start_time(self, obj):
        return obj.worker_profile.work_start_time if hasattr(obj, 'worker_profile') else None
    
    def get_work_end_time(self, obj):
        return obj.worker_profile.work_end_time if hasattr(obj, 'worker_profile') else None
    
    def get_latitude(self, obj):
        return obj.worker_profile.latitude if hasattr(obj, 'worker_profile') else None
    
    def get_longitude(self, obj):
        return obj.worker_profile.longitude if hasattr(obj, 'worker_profile') else None
    
    def get_total_jobs_completed(self, obj):
        return obj.worker_profile.total_jobs_completed if hasattr(obj, 'worker_profile') else 0
    
    def get_average_rating(self, obj):
        return float(obj.worker_profile.average_rating) if hasattr(obj, 'worker_profile') else 0.0
    
    def get_total_reviews(self, obj):
        return obj.worker_profile.total_reviews if hasattr(obj, 'worker_profile') else 0
    
    def get_is_verified(self, obj):
        return obj.worker_profile.is_verified if hasattr(obj, 'worker_profile') else False
    
    def get_is_available(self, obj):
        return obj.worker_profile.is_available if hasattr(obj, 'worker_profile') else False
    
    def get_is_online(self, obj):
        return obj.worker_profile.is_online if hasattr(obj, 'worker_profile') else False
    
    def get_last_seen(self, obj):
        return obj.worker_profile.last_seen if hasattr(obj, 'worker_profile') else obj.last_login
    
    def get_completion_rate(self, obj):
        if hasattr(obj, 'worker_profile'):
            completed = obj.worker_profile.total_jobs_completed
            if completed == 0:
                return 100.0
            return min(100.0, 85.0 + (completed * 0.5))
        return 100.0
    
    def get_response_time(self, obj):
        if hasattr(obj, 'worker_profile') and obj.worker_profile.is_online:
            return "< 1 heure"
        return "< 24 heures"


class WorkerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating worker profiles
    محول لتحديث ملف العامل
    """
    services = WorkerServiceSerializer(many=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'services'
        ]
    
    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', [])
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update services if provided
        if services_data and hasattr(instance, 'worker_services'):
            # Clear existing services and recreate
            instance.worker_services.all().delete()
            for service_data in services_data:
                WorkerService.objects.create(worker=instance, **service_data)
        
        return instance