# clients/serializers.py 
from rest_framework import serializers
from django.utils import timezone
from .models import FavoriteWorker, ClientSettings
from users.models import User,ClientProfile  


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    Client profile serializer - simplified version
    """
    # User information
    phone = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    # Client profile data - writable
    gender = serializers.ChoiceField(
        choices=['male', 'female'],
        required=False,
        allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )
    notifications_enabled = serializers.BooleanField(required=False)
    
    # Read-only computed fields
    profile_image_url = serializers.SerializerMethodField(read_only=True)
    total_tasks_published = serializers.SerializerMethodField(read_only=True)
    total_tasks_completed = serializers.SerializerMethodField(read_only=True)
    total_amount_spent = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    member_since = serializers.SerializerMethodField(read_only=True)
    success_rate = serializers.SerializerMethodField(read_only=True)
    
    # ✅✅✅ إضافة حقول Online ✅✅✅
    is_online = serializers.BooleanField(read_only=True)
    last_seen = serializers.DateTimeField(read_only=True)
    # ✅✅✅ نهاية الإضافة ✅✅✅
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'first_name', 'last_name', 'full_name',
            'gender', 'address', 'emergency_contact',
            'profile_image_url', 'is_verified', 'total_tasks_published',
            'total_tasks_completed', 'total_amount_spent', 'success_rate',
            'notifications_enabled', 'member_since',
            'is_online', 'last_seen',  # ✅ إضافة
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'phone', 'is_verified', 'total_tasks_published',
            'total_tasks_completed', 'total_amount_spent', 'success_rate',
            'member_since', 'created_at', 'updated_at', 'profile_image_url',
            'full_name', 'is_online', 'last_seen'  # ✅ إضافة
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.partial = True
    
    # Getter methods
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
    
    def get_total_tasks_published(self, obj):
        """حساب عدد المهام المنشورة من قاعدة البيانات"""
        from tasks.models import ServiceRequest
        count = ServiceRequest.objects.filter(client=obj).count()
        print(f'📊 Tasks published for client {obj.id}: {count}')
        return count

    def get_total_tasks_completed(self, obj):
        
        # نعيد 0 دائماً لأن النظام لم يعد يتتبع الإكمال
        return 0

    def get_total_amount_spent(self, obj):
        """
        ❌ النظام الجديد: لا توجد مدفوعات بين العميل والعامل
        فقط اشتراك شهري (8 MRU/شهر) للمنصة
        """
        return "0.00"

    def get_success_rate(self, obj):
        if hasattr(obj, 'client_profile'):
            profile = obj.client_profile
            if profile.total_tasks_published == 0:
                return 0.0
            return round((profile.total_tasks_completed / profile.total_tasks_published) * 100, 1)
        return 0.0
    
    def to_representation(self, instance):
        """Override to include ClientProfile data in GET response"""
        data = super().to_representation(instance)
        
        # Add ClientProfile fields to response
        if hasattr(instance, 'client_profile'):
            profile = instance.client_profile
            data['gender'] = profile.gender or ''
            data['address'] = profile.address or ''
            data['emergency_contact'] = profile.emergency_contact or ''
            data['notifications_enabled'] = profile.notifications_enabled
            # ✅✅✅ إضافة حقول Online ✅✅✅
            data['is_online'] = profile.is_online
            data['last_seen'] = profile.last_seen
            # ✅✅✅ نهاية الإضافة ✅✅✅
        else:
            # Defaults if no profile exists
            data['gender'] = ''
            data['address'] = ''
            data['emergency_contact'] = ''
            data['notifications_enabled'] = True
            # ✅✅✅ إضافة قيم افتراضية ✅✅✅
            data['is_online'] = False
            data['last_seen'] = None
            # ✅✅✅ نهاية الإضافة ✅✅✅
        
        return data
    
    def update(self, instance, validated_data):
        """Update user and client profile"""
        
        # 1. Update User fields
        user_fields = ['first_name', 'last_name']
        for field in user_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        
        # 2. Update ClientProfile fields
        profile, created = ClientProfile.objects.get_or_create(user=instance)
        
        profile_fields = ['gender', 'address', 'emergency_contact', 'notifications_enabled']
        
        for field in profile_fields:
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        
        profile.save()
        
        # 3. Refresh to get updated data
        instance.refresh_from_db()
        
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
    phone = serializers.SerializerMethodField()
    
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
            'startingPrice', 'lastSeen', 'notes','phone' 
        ]
        read_only_fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 'location',
            'completedJobs', 'isOnline', 'profileImage', 'services',
            'addedAt', 'timesHired', 'totalSpent',
            'startingPrice', 'lastSeen','phone' 
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
        worker = obj.worker
        services_list = []
        
        # من WorkerService
        if hasattr(worker, 'worker_services'):
            services = worker.worker_services.filter(is_active=True)
            if services.exists():
                services_list = [service.category.name for service in services]
        
        # من WorkerProfile إذا كانت فارغة
        if not services_list and hasattr(worker, 'worker_profile'):
            service_cat = worker.worker_profile.service_category
            if service_cat:  # هو string مباشرة
                services_list = [service_cat]  # أضفه كما هو
        
        return services_list
    
    
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
    
    # بعد دالة get_lastSeen، أضف:

    def get_phone(self, obj):
        """Get worker phone number"""
        return obj.worker.phone


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