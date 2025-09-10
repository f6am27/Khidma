# clients/serializers.py - مُصحح للنظام الجديد
from rest_framework import serializers
from django.utils import timezone
from .models import FavoriteWorker, ClientSettings
from users.models import User


# clients/serializers.py - مُصحح للنظام الجديد
from rest_framework import serializers
from django.utils import timezone
from .models import FavoriteWorker, ClientSettings
from users.models import User


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    Client profile serializer for detailed view with partial update support
    محول ملف العميل المفصل مع دعم التحديث الجزئي
    """
    # User information
    phone = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    # Client profile data
    bio = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    emergency_contact = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    total_tasks_published = serializers.SerializerMethodField()
    total_tasks_completed = serializers.SerializerMethodField()
    total_amount_spent = serializers.SerializerMethodField()
    preferred_language = serializers.SerializerMethodField()
    notifications_enabled = serializers.SerializerMethodField()
    
    # Computed fields
    full_name = serializers.SerializerMethodField()
    member_since = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'bio', 'date_of_birth', 'gender', 'address', 'emergency_contact',
            'profile_image_url', 'is_verified', 'total_tasks_published',
            'total_tasks_completed', 'total_amount_spent', 'success_rate',
            'preferred_language', 'notifications_enabled', 'member_since',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'phone', 'is_verified', 'total_tasks_published',
            'total_tasks_completed', 'total_amount_spent', 'success_rate',
            'member_since', 'created_at', 'updated_at'
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
        if hasattr(obj, 'client_profile') and obj.client_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.client_profile.profile_image.url)
            return obj.client_profile.profile_image.url
        return None
    
    # ClientProfile field getters
    def get_bio(self, obj):
        return obj.client_profile.bio if hasattr(obj, 'client_profile') else ""
    
    def get_date_of_birth(self, obj):
        return obj.client_profile.date_of_birth if hasattr(obj, 'client_profile') else None
    
    def get_gender(self, obj):
        return obj.client_profile.gender if hasattr(obj, 'client_profile') else ""
    
    def get_address(self, obj):
        return obj.client_profile.address if hasattr(obj, 'client_profile') else ""
    
    def get_emergency_contact(self, obj):
        return obj.client_profile.emergency_contact if hasattr(obj, 'client_profile') else ""
    
    def get_total_tasks_published(self, obj):
        return obj.client_profile.total_tasks_published if hasattr(obj, 'client_profile') else 0
    
    def get_total_tasks_completed(self, obj):
        return obj.client_profile.total_tasks_completed if hasattr(obj, 'client_profile') else 0
    
    def get_total_amount_spent(self, obj):
        return str(obj.client_profile.total_amount_spent) if hasattr(obj, 'client_profile') else "0.00"
    
    def get_preferred_language(self, obj):
        return obj.client_profile.preferred_language if hasattr(obj, 'client_profile') else "fr"
    
    def get_notifications_enabled(self, obj):
        return obj.client_profile.notifications_enabled if hasattr(obj, 'client_profile') else True
    
    def get_success_rate(self, obj):
        if hasattr(obj, 'client_profile'):
            profile = obj.client_profile
            if profile.total_tasks_published == 0:
                return 0.0
            return round((profile.total_tasks_completed / profile.total_tasks_published) * 100, 1)
        return 0.0
    
    def update(self, instance, validated_data):
        """Update user and client profile with nested data (partial support)"""
        # Update user fields
        user_fields = ['first_name', 'last_name']
        for field in user_fields:
            if field in validated_data and validated_data[field] is not None:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance


class FavoriteWorkerSerializer(serializers.ModelSerializer):
    """
    Favorite worker serializer with worker details
    محول العامل المفضل مع تفاصيل العامل
    """
    # Worker information
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    completedJobs = serializers.SerializerMethodField()
    isOnline = serializers.SerializerMethodField()
    profileImage = serializers.SerializerMethodField()
    
    # Services
    services = serializers.SerializerMethodField()
    
    # Favorite-specific data
    addedAt = serializers.DateTimeField(source='added_at', read_only=True)
    timesHired = serializers.IntegerField(source='times_hired', read_only=True)
    totalSpent = serializers.DecimalField(source='total_spent_with_worker', max_digits=10, decimal_places=2, read_only=True)
    
    # Starting price (from worker services)
    startingPrice = serializers.SerializerMethodField()
    lastSeen = serializers.SerializerMethodField()
    
    class Meta:
        model = FavoriteWorker
        fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 'location',
            'completedJobs', 'isOnline', 'profileImage', 'services',
            'addedAt', 'timesHired', 'totalSpent',
            'startingPrice', 'lastSeen', 'notes'
        ]
        read_only_fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 'location',
            'completedJobs', 'isOnline', 'profileImage', 'services',
            'addedAt', 'timesHired', 'totalSpent',
            'startingPrice', 'lastSeen'
        ]
    
    def get_name(self, obj):
        """Get worker full name"""
        return obj.worker.get_full_name() or obj.worker.phone
    
    def get_rating(self, obj):
        """Get worker rating"""
        if hasattr(obj.worker, 'worker_profile'):
            return float(obj.worker.worker_profile.average_rating)
        return 0.0
    
    def get_reviewCount(self, obj):
        """Get worker review count"""
        if hasattr(obj.worker, 'worker_profile'):
            return obj.worker.worker_profile.total_reviews
        return 0
    
    def get_location(self, obj):
        """Get worker location"""
        if hasattr(obj.worker, 'worker_profile'):
            return obj.worker.worker_profile.service_area
        return ""
    
    def get_completedJobs(self, obj):
        """Get worker completed jobs"""
        if hasattr(obj.worker, 'worker_profile'):
            return obj.worker.worker_profile.total_jobs_completed
        return 0
    
    def get_isOnline(self, obj):
        """Get worker online status"""
        if hasattr(obj.worker, 'worker_profile'):
            return obj.worker.worker_profile.is_online
        return False
    
    def get_profileImage(self, obj):
        """Get worker profile image URL"""
        if hasattr(obj.worker, 'worker_profile') and obj.worker.worker_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker.worker_profile.profile_image.url)
            return obj.worker.worker_profile.profile_image.url
        return None
    
    def get_services(self, obj):
        """Get worker services"""
        if hasattr(obj.worker, 'worker_services'):
            return [service.category.name for service in obj.worker.worker_services.filter(is_active=True)]
        return []
    
    def get_startingPrice(self, obj):
        """Get worker's minimum price"""
        if hasattr(obj.worker, 'worker_services'):
            services = obj.worker.worker_services.filter(is_active=True)
            if services.exists():
                return min(float(service.base_price) for service in services)
        return 0
    
    def get_lastSeen(self, obj):
        """Get worker's last activity"""
        if hasattr(obj.worker, 'worker_profile'):
            return obj.worker.worker_profile.last_seen
        return obj.worker.last_login


class FavoriteWorkerCreateSerializer(serializers.ModelSerializer):
    """
    Add worker to favorites serializer
    محول إضافة عامل للمفضلة
    """
    worker_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FavoriteWorker
        fields = ['worker_id', 'notes']
        extra_kwargs = {
            'notes': {'required': False, 'allow_blank': True}
        }
    
    def validate_worker_id(self, value):
        """Validate worker exists and is active"""
        try:
            worker = User.objects.get(id=value, role='worker', is_verified=True)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Worker not found or not available")
    
    def validate(self, data):
        """Check if worker is not already in favorites"""
        request = self.context.get('request')
        client = request.user
        worker_id = data['worker_id']
        
        if FavoriteWorker.objects.filter(client=client, worker_id=worker_id).exists():
            raise serializers.ValidationError("Ce prestataire est déjà dans vos favoris")
        
        return data
    
    def create(self, validated_data):
        """Create favorite worker relationship"""
        request = self.context.get('request')
        client = request.user
        worker_id = validated_data.pop('worker_id')
        worker = User.objects.get(id=worker_id)
        
        return FavoriteWorker.objects.create(
            client=client,
            worker=worker,
            **validated_data
        )


class ClientSettingsSerializer(serializers.ModelSerializer):
    """
    Client settings serializer with partial update support
    محول إعدادات العميل مع دعم التحديث الجزئي
    """
    class Meta:
        model = ClientSettings
        fields = [
            'push_notifications', 'email_notifications', 'sms_notifications',
            'theme_preference', 'language', 'profile_visibility',
            'allow_contact_from_workers', 'auto_detect_location', 'search_radius_km'
        ]
    
    def __init__(self, *args, **kwargs):
        """Initialize with partial update support"""
        super().__init__(*args, **kwargs)
        # Enable partial updates
        self.partial = True
        
        # Make all fields optional
        for field_name, field in self.fields.items():
            field.required = False
    
    def update(self, instance, validated_data):
        """Update client settings (partial support)"""
        for attr, value in validated_data.items():
            if value is not None:  # Only update if value is provided
                setattr(instance, attr, value)
        instance.save()
        return instance