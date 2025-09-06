# clients/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ClientProfile, FavoriteWorker, ClientSettings
from accounts.models import Profile
from workers.models import WorkerProfile


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    Client profile serializer (detailed view) with partial update support
    محول ملف العميل المفصل مع دعم التحديث الجزئي
    """
    # User information
    username = serializers.CharField(source='profile.user.username', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    first_name = serializers.CharField(source='profile.user.first_name', required=False)
    last_name = serializers.CharField(source='profile.user.last_name', required=False)
    
    # Computed fields
    full_name = serializers.ReadOnlyField()
    member_since = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    
    # Profile image URL
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientProfile
        fields = [
            'id', 'username', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'bio', 'date_of_birth', 'gender', 'address',
            'emergency_contact', 'profile_image_url', 'is_verified',
            'total_tasks_published', 'total_tasks_completed', 'total_amount_spent',
            'success_rate', 'is_active', 'last_activity',
            'preferred_language', 'notifications_enabled', 'email_notifications',
            'sms_notifications', 'member_since', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'phone', 'is_verified', 'total_tasks_published',
            'total_tasks_completed', 'total_amount_spent',
            'success_rate', 'last_activity', 'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        """Initialize with partial=True for updates"""
        super().__init__(*args, **kwargs)
        # Enable partial updates for all fields
        self.partial = True
        
        # Make all non-read-only fields optional
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.read_only_fields:
                field.required = False
    
    def get_profile_image_url(self, obj):
        """Get profile image URL"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def update(self, instance, validated_data):
        """Update client profile with nested user data (partial support)"""
        # Extract user data
        profile_data = validated_data.pop('profile', {})
        user_data = profile_data.pop('user', {})
        
        # Update user fields only if provided
        if user_data:
            user = instance.profile.user
            for attr, value in user_data.items():
                if value is not None:  # Only update if value is provided
                    setattr(user, attr, value)
            user.save()
        
        # Update client profile fields only if provided
        for attr, value in validated_data.items():
            if value is not None:  # Only update if value is provided
                setattr(instance, attr, value)
        
        instance.save()
        return instance


class ClientBasicSerializer(serializers.ModelSerializer):
    """
    Basic client info for public display
    معلومات العميل الأساسية للعرض العام
    """
    full_name = serializers.ReadOnlyField()
    profile_image_url = serializers.SerializerMethodField()
    member_since = serializers.ReadOnlyField()
    
    class Meta:
        model = ClientProfile
        fields = [
            'id', 'full_name', 'profile_image_url', 'is_verified',
            'total_tasks_completed', 'member_since'
        ]
    
    def get_profile_image_url(self, obj):
        """Get profile image URL"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class FavoriteWorkerSerializer(serializers.ModelSerializer):
    """
    Favorite worker serializer with worker details
    محول العامل المفضل مع تفاصيل العامل
    """
    # Worker information
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    name = serializers.SerializerMethodField()
    rating = serializers.DecimalField(source='worker.average_rating', max_digits=3, decimal_places=1, read_only=True)
    reviewCount = serializers.IntegerField(source='worker.total_reviews', read_only=True)
    location = serializers.CharField(source='worker.service_area', read_only=True)
    completedJobs = serializers.IntegerField(source='worker.total_jobs_completed', read_only=True)
    isOnline = serializers.BooleanField(source='worker.is_online', read_only=True)
    profileImage = serializers.SerializerMethodField()
    
    # Services
    services = serializers.SerializerMethodField()
    
    # Favorite-specific data
    addedAt = serializers.DateTimeField(source='added_at', read_only=True)
    relationshipDuration = serializers.ReadOnlyField(source='relationship_duration')
    timesHired = serializers.IntegerField(source='times_hired', read_only=True)
    totalSpent = serializers.DecimalField(source='total_spent_with_worker', max_digits=10, decimal_places=2, read_only=True)
    lastRating = serializers.IntegerField(source='last_rating_given', read_only=True)
    
    # Starting price (from worker services)
    startingPrice = serializers.SerializerMethodField()
    lastSeen = serializers.SerializerMethodField()
    
    class Meta:
        model = FavoriteWorker
        fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 'location',
            'completedJobs', 'isOnline', 'profileImage', 'services',
            'addedAt', 'relationshipDuration', 'timesHired', 'totalSpent',
            'lastRating', 'startingPrice', 'lastSeen', 'notes'
        ]
        read_only_fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 'location',
            'completedJobs', 'isOnline', 'profileImage', 'services',
            'addedAt', 'relationshipDuration', 'timesHired', 'totalSpent',
            'lastRating', 'startingPrice', 'lastSeen'
        ]
    
    def get_name(self, obj):
        """Get worker full name"""
        user = obj.worker.profile.user
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_profileImage(self, obj):
        """Get worker profile image URL"""
        if obj.worker.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.worker.profile_image.url)
            return obj.worker.profile_image.url
        return None
    
    def get_services(self, obj):
        """Get worker services"""
        return [service.category.name for service in obj.worker.services.all()]
    
    def get_startingPrice(self, obj):
        """Get worker's minimum price"""
        services = obj.worker.services.all()
        if services:
            return min(service.price for service in services)
        return 0
    
    def get_lastSeen(self, obj):
        """Get worker's last activity"""
        return obj.worker.profile.last_login if obj.worker.profile.last_login else obj.worker.created_at


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
            worker = WorkerProfile.objects.get(id=value, is_available=True)
            return value
        except WorkerProfile.DoesNotExist:
            raise serializers.ValidationError("Worker not found or not available")
    
    def validate(self, data):
        """Check if worker is not already in favorites"""
        request = self.context.get('request')
        client = request.user.profile
        worker_id = data['worker_id']
        
        if FavoriteWorker.objects.filter(client=client, worker_id=worker_id).exists():
            raise serializers.ValidationError("Ce prestataire est déjà dans vos favoris")
        
        return data
    
    def create(self, validated_data):
        """Create favorite worker relationship"""
        request = self.context.get('request')
        client = request.user.profile
        worker_id = validated_data.pop('worker_id')
        worker = WorkerProfile.objects.get(id=worker_id)
        
        return FavoriteWorker.objects.create(
            client=client,
            worker=worker,
            **validated_data
        )


class ClientStatsSerializer(serializers.ModelSerializer):
    """
    Client statistics serializer
    محول إحصائيات العميل
    """
    # Task statistics
    published_tasks = serializers.IntegerField(source='total_tasks_published', read_only=True)
    completed_tasks = serializers.IntegerField(source='total_tasks_completed', read_only=True)
    cancelled_tasks = serializers.SerializerMethodField()
    active_tasks = serializers.SerializerMethodField()
    
    # Financial statistics
    total_spent = serializers.DecimalField(source='total_amount_spent', max_digits=10, decimal_places=2, read_only=True)
    average_task_value = serializers.SerializerMethodField()
    
    # Relationship statistics
    favorite_workers_count = serializers.SerializerMethodField()
    most_hired_worker = serializers.SerializerMethodField()
    
    # Activity statistics
    success_rate = serializers.ReadOnlyField()
    member_since = serializers.ReadOnlyField()
    days_active = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientProfile
        fields = [
            'published_tasks', 'completed_tasks', 'cancelled_tasks', 'active_tasks',
            'total_spent', 'average_task_value',
            'favorite_workers_count', 'most_hired_worker',
            'success_rate', 'member_since', 'days_active'
        ]
    
    def get_cancelled_tasks(self, obj):
        """Get cancelled tasks count"""
        from tasks.models import ServiceRequest
        return ServiceRequest.objects.filter(
            client=obj.profile,
            status='cancelled'
        ).count()
    
    def get_active_tasks(self, obj):
        """Get active tasks count"""
        from tasks.models import ServiceRequest
        return ServiceRequest.objects.filter(
            client=obj.profile,
            status__in=['published', 'active', 'work_completed']
        ).count()
    
    def get_average_task_value(self, obj):
        """Calculate average task value"""
        from tasks.models import ServiceRequest
        completed_tasks = ServiceRequest.objects.filter(
            client=obj.profile,
            status='completed'
        )
        
        if completed_tasks.exists():
            total_value = sum(task.budget for task in completed_tasks)
            return round(total_value / completed_tasks.count(), 2)
        return 0.0
    
    def get_favorite_workers_count(self, obj):
        """Get favorite workers count"""
        return obj.profile.favorite_workers.count()
    
    def get_most_hired_worker(self, obj):
        """Get most frequently hired worker"""
        favorite = obj.profile.favorite_workers.order_by('-times_hired').first()
        if favorite:
            return {
                'name': favorite.worker_full_name,
                'times_hired': favorite.times_hired,
                'total_spent': float(favorite.total_spent_with_worker)
            }
        return None
    
    def get_days_active(self, obj):
        """Calculate days since registration"""
        days = (timezone.now().date() - obj.created_at.date()).days
        return days


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
            'show_last_seen', 'allow_contact_from_workers',
            'auto_detect_location', 'search_radius_km'
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