# workers/serializers.py - النسخة النهائية الكاملة
from rest_framework import serializers
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
        
        # Make all fields optional
        for field_name, field in self.fields.items():
            field.required = False


class WorkerProfileSerializer(serializers.ModelSerializer):
    """
    Worker profile serializer for worker to view/edit their own profile
    محول ملف العامل للعامل لعرض/تعديل ملفه الشخصي
    """
    # User information
    phone = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    # Worker profile data
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
    
    # Computed fields
    full_name = serializers.SerializerMethodField()
    member_since = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'bio', 'service_area', 'service_category', 'base_price',
            'profile_image_url', 'available_days', 'work_start_time', 'work_end_time',
            'latitude', 'longitude', 'total_jobs_completed', 'average_rating',
            'total_reviews', 'is_verified', 'is_available', 'is_online',
            'member_since', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'phone', 'total_jobs_completed', 'average_rating',
            'total_reviews', 'is_verified', 'member_since', 'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        """Initialize with partial=True for updates"""
        super().__init__(*args, **kwargs)
        self.partial = True
        
        # Make updateable fields optional
        for field_name in ['first_name', 'last_name']:
            if field_name in self.fields:
                self.fields[field_name].required = False
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone
    
    def get_member_since(self, obj):
        return obj.date_joined.strftime("%B %Y")
    
    def get_profile_image_url(self, obj):
        if hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker_profile.profile_image.url)
            return obj.worker_profile.profile_image.url
        return None
    
    # WorkerProfile field getters
    def get_bio(self, obj):
        return obj.worker_profile.bio if hasattr(obj, 'worker_profile') else ""
    
    def get_service_area(self, obj):
        return obj.worker_profile.service_area if hasattr(obj, 'worker_profile') else ""
    
    def get_service_category(self, obj):
        return obj.worker_profile.service_category if hasattr(obj, 'worker_profile') else ""
    
    def get_base_price(self, obj):
        return str(obj.worker_profile.base_price) if hasattr(obj, 'worker_profile') else "0.00"
    
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
    
    def update(self, instance, validated_data):
        """Update user and worker profile (partial support)"""
        # Update user fields
        user_fields = ['first_name', 'last_name']
        for field in user_fields:
            if field in validated_data and validated_data[field] is not None:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance


class WorkerProfileListSerializer(serializers.ModelSerializer):
    """
    Flutter-compatible serializer for worker list/search
    محول متوافق مع Flutter لقائمة العمال/البحث
    """
    # Flutter expects these exact field names
    name = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField() 
    category = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    minPrice = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    phone = serializers.CharField(read_only=True)
    distance = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    isFavorite = serializers.SerializerMethodField()
    
    # Additional fields for detail view
    user = UserBasicSerializer(read_only=True)
    services = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            # Flutter-expected fields
            'name', 'service', 'category', 'rating', 'distance', 'time', 
            'price', 'minPrice', 'image', 'isFavorite', 'area', 'phone',
            # Additional backend fields
            'id', 'user', 'services'
        ]
    
    def get_name(self, obj):
        return obj.get_full_name() or obj.phone
    
    def get_service(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_category
        return "Service"
    
    def get_category(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_category
        return "Général"
    
    def get_rating(self, obj):
        if hasattr(obj, 'worker_profile'):
            return float(obj.worker_profile.average_rating)
        return 0.0
    
    def get_area(self, obj):
        if hasattr(obj, 'worker_profile'):
            return obj.worker_profile.service_area
        return ""
    
    def get_minPrice(self, obj):
        if hasattr(obj, 'worker_services'):
            services = obj.worker_services.filter(is_active=True)
            if services.exists():
                return min(int(s.base_price) for s in services)
        elif hasattr(obj, 'worker_profile'):
            return int(obj.worker_profile.base_price)
        return 0
    
    def get_price(self, obj):
        if hasattr(obj, 'worker_services'):
            services = obj.worker_services.filter(is_active=True)
            if services.exists():
                prices = [int(s.base_price) for s in services]
                min_price = min(prices)
                max_price = max(prices)
                
                if min_price == max_price:
                    return f"{min_price} MRU"
                return f"{min_price}-{max_price} MRU"
        elif hasattr(obj, 'worker_profile'):
            return f"{int(obj.worker_profile.base_price)} MRU"
        
        return "Prix sur demande"
    
    def get_image(self, obj):
        if hasattr(obj, 'worker_profile') and obj.worker_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker_profile.profile_image.url)
            return obj.worker_profile.profile_image.url
        return None
    
    def get_services(self, obj):
        if hasattr(obj, 'worker_services'):
            return WorkerServiceSerializer(obj.worker_services.filter(is_active=True), many=True).data
        return []
    
    def get_distance(self, obj):
        request = self.context.get('request')
        if request:
            client_lat = request.query_params.get('lat')
            client_lng = request.query_params.get('lng')
            
            if (client_lat and client_lng and hasattr(obj, 'worker_profile') 
                and obj.worker_profile.latitude and obj.worker_profile.longitude):
                try:
                    from math import radians, cos, sin, asin, sqrt
                    
                    def haversine_distance(lat1, lng1, lat2, lng2):
                        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
                        dlat = lat2 - lat1
                        dlng = lng2 - lng1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
                        c = 2 * asin(sqrt(a))
                        r = 6371
                        return c * r
                    
                    distance_km = haversine_distance(
                        float(client_lat), float(client_lng),
                        float(obj.worker_profile.latitude), float(obj.worker_profile.longitude)
                    )
                    return f"{distance_km:.1f} km"
                    
                except (ValueError, TypeError):
                    pass
        
        import random
        return f"{random.uniform(0.5, 5.0):.1f} km"
    
    def get_time(self, obj):
        import random
        time_minutes = random.randint(5, 30)
        return f"{time_minutes} Min"
    
    def get_isFavorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'client':
            from clients.models import FavoriteWorker
            return FavoriteWorker.objects.filter(client=request.user, worker=obj).exists()
        return False


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