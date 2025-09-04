# workers/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import WorkerProfile, WorkerService, WorkerGallery, WorkerExperience
from accounts.models import Profile
from services.serializers import ServiceCategorySerializer


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user info for worker display
    معلومات المستخدم الأساسية لعرض العامل
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'date_joined']


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


class WorkerExperienceSerializer(serializers.ModelSerializer):
    """
    Worker experience entries
    خبرات العمل للعامل
    """
    class Meta:
        model = WorkerExperience
        fields = [
            'id', 'title', 'description', 'start_date', 
            'end_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkerProfileListSerializer(serializers.ModelSerializer):
    """
    Flutter-compatible serializer for worker list/search
    محول متوافق مع Flutter لقائمة العمال/البحث
    """
    # Flutter expects these exact field names
    name = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField() 
    category = serializers.SerializerMethodField()
    rating = serializers.DecimalField(source='average_rating', max_digits=3, decimal_places=1, read_only=True)
    minPrice = serializers.SerializerMethodField()
    area = serializers.CharField(source='service_area', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    distance = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    image = serializers.CharField(source='profile_image', read_only=True)
    isFavorite = serializers.SerializerMethodField()
    
    # Additional fields for detail view
    user = UserBasicSerializer(read_only=True)
    services = WorkerServiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = [
            # Flutter-expected fields (matching Flutter topWorkers structure)
            'name', 'service', 'category', 'rating', 'distance', 'time', 
            'price', 'minPrice', 'image', 'isFavorite', 'area', 'phone',
            # Additional backend fields
            'id', 'user', 'bio', 'profile_image', 'total_jobs_completed', 
            'total_reviews', 'is_verified', 'is_available', 'is_online', 
            'last_seen', 'services'
        ]
    
    def get_name(self, obj):
        """Get worker's full name"""
        user = obj.profile.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_service(self, obj):
        """Get primary service name (for Flutter compatibility)"""
        first_service = obj.services.filter(is_active=True).first()
        return first_service.category.name if first_service else "Service"
    
    def get_category(self, obj):
        """Get primary service category (for Flutter compatibility)"""  
        first_service = obj.services.filter(is_active=True).first()
        return first_service.category.name if first_service else "Général"
    
    def get_minPrice(self, obj):
        """Get minimum price (for sorting)"""
        first_service = obj.services.filter(is_active=True).first()
        return int(first_service.base_price) if first_service else 0
    
    def get_price(self, obj):
        """Get price range string (Flutter format)"""
        services = obj.services.filter(is_active=True)
        if not services.exists():
            return "Prix sur demande"
        
        prices = [int(s.base_price) for s in services]
        min_price = min(prices)
        max_price = max(prices)
        
        if min_price == max_price:
            return f"{min_price} MRU"
        return f"{min_price}-{max_price} MRU"
    
    def get_distance(self, obj):
        """Calculate real distance from client if coordinates available"""
        # Get client coordinates from request context if available
        request = self.context.get('request')
        if request:
            client_lat = request.query_params.get('lat')
            client_lng = request.query_params.get('lng')
            
            if client_lat and client_lng and obj.latitude and obj.longitude:
                try:
                    from math import radians, cos, sin, asin, sqrt
                    
                    def haversine_distance(lat1, lng1, lat2, lng2):
                        # convert decimal degrees to radians 
                        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
                        
                        # haversine formula 
                        dlat = lat2 - lat1
                        dlng = lng2 - lng1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
                        c = 2 * asin(sqrt(a))
                        r = 6371 # Radius of earth in kilometers
                        return c * r
                    
                    distance_km = haversine_distance(
                        float(client_lat), float(client_lng),
                        float(obj.latitude), float(obj.longitude)
                    )
                    return f"{distance_km:.1f} km"
                    
                except (ValueError, TypeError):
                    pass
        
        # Fallback to mock distance if no real coordinates
        import random
        return f"{random.uniform(0.5, 5.0):.1f} km"
    
    def get_time(self, obj):
        """Get estimated time to reach (mock for now)"""
        # Extract number from distance and calculate time
        import random
        time_minutes = random.randint(5, 30)
        return f"{time_minutes} Min"
    
    def get_isFavorite(self, obj):
        """Check if worker is in user's favorites (default false for now)"""
        # TODO: Implement real favorites check when user authentication is added
        return False


class WorkerProfileDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for worker profile view
    محول مفصل لعرض ملف العامل
    """
    user = UserBasicSerializer(read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    services = WorkerServiceSerializer(many=True, read_only=True)
    gallery = WorkerGallerySerializer(many=True, read_only=True)
    experiences = WorkerExperienceSerializer(many=True, read_only=True)
    
    # Computed fields
    completion_rate = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkerProfile
        fields = [
            'id', 'user', 'phone', 'bio', 'service_area', 'profile_image',
            'available_days', 'work_start_time', 'work_end_time',
            'latitude', 'longitude',
            'total_jobs_completed', 'average_rating', 'total_reviews',
            'is_verified', 'is_available', 'is_online', 'last_seen',
            'services', 'gallery', 'experiences',
            'completion_rate', 'response_time',
            'created_at', 'updated_at'
        ]
    
    def get_completion_rate(self, obj):
        """Mock completion rate - replace with real calculation later"""
        if obj.total_jobs_completed == 0:
            return 100.0
        # Mock high completion rate for established workers
        return min(100.0, 85.0 + (obj.total_jobs_completed * 0.5))
    
    def get_response_time(self, obj):
        """Mock response time - replace with real data later"""
        if obj.is_online:
            return "< 1 heure"
        return "< 24 heures"


class WorkerProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating worker profiles (for onboarding)
    محول لإنشاء/تحديث ملف العامل (للتسجيل)
    """
    services = WorkerServiceSerializer(many=True, required=False)
    
    class Meta:
        model = WorkerProfile
        fields = [
            'bio', 'service_area', 'profile_image',
            'available_days', 'work_start_time', 'work_end_time',
            'latitude', 'longitude', 'is_available',
            'services'
        ]
    
    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        worker_profile = WorkerProfile.objects.create(**validated_data)
        
        # Create associated services
        for service_data in services_data:
            WorkerService.objects.create(worker=worker_profile, **service_data)
        
        return worker_profile
    
    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', [])
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update services if provided
        if services_data:
            # Clear existing services and recreate (simple approach)
            instance.services.all().delete()
            for service_data in services_data:
                WorkerService.objects.create(worker=instance, **service_data)
        
        return instance