# tasks/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification
from users.models import User
from services.serializers import ServiceCategorySerializer


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user info for task display
    معلومات المستخدم الأساسية لعرض المهمة
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'date_joined']


class TaskApplicationSerializer(serializers.ModelSerializer):
    """
    Worker application serializer (simplified for candidates view)
    محول تقدم العامل (مبسط لعرض المتقدمين)
    """
    # Worker info (Flutter-compatible)
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    name = serializers.SerializerMethodField()
    rating = serializers.DecimalField(source='worker.average_rating', max_digits=3, decimal_places=1, read_only=True)
    reviewCount = serializers.IntegerField(source='worker.total_reviews', read_only=True)
    location = serializers.SerializerMethodField()
    completedJobs = serializers.IntegerField(source='worker.total_jobs_completed', read_only=True)
    isOnline = serializers.BooleanField(source='worker.is_online', read_only=True)
    profileImage = serializers.CharField(source='worker.profile_image', read_only=True)
    
    # Application details (simplified)
    id = serializers.CharField(source='worker.id', read_only=True)
    applicationMessage = serializers.CharField(source='application_message', read_only=True)
    
    class Meta:
        model = TaskApplication
        fields = [
            'id', 'worker_id', 'name', 'rating', 'reviewCount', 
            'location', 'completedJobs', 'applicationMessage', 
            'isOnline', 'profileImage', 'applied_at', 'application_status'
        ]
    
    def get_name(self, obj):
        """Worker full name"""
        user = obj.worker
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_location(self, obj):
        """Worker location with distance"""
        # Extract area from service_area
        area = obj.worker.service_area.split(',')[0].strip()
        # Mock distance for now - can be calculated later
        import random
        distance = random.uniform(0.5, 5.0)
        return f"{area}, {distance:.1f}km"


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """
    Service request list serializer (Flutter-compatible)
    محول قائمة طلبات الخدمة (متوافق مع Flutter)
    """
    # Flutter-compatible field names
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    status = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    assignedProvider = serializers.SerializerMethodField()
    providerRating = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'budget', 
            'location', 'preferredTime', 'status', 'createdAt',
            'applicantsCount', 'assignedProvider', 'providerRating'
        ]
        extra_kwargs = {
            'preferredTime': {'source': 'preferred_time'},
        }
    
    def get_assignedProvider(self, obj):
        """Assigned worker name"""
        if obj.assigned_worker:
            user = obj.assigned_worker
            if user.first_name and user.last_name:
                return f"{user.first_name} {user.last_name}"
            return user.username
        return None
    
    def get_providerRating(self, obj):
        """Assigned worker rating"""
        if obj.assigned_worker:
            return int(obj.assigned_worker.average_rating)
        return None


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    """
    Detailed service request serializer
    محول تفاصيل طلب الخدمة
    """
    # Client info
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    
    # Service info
    service_category = ServiceCategorySerializer(read_only=True)
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    
    # Status and timing
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    
    # Assigned worker info
    assigned_worker_info = serializers.SerializerMethodField()
    
    # Applications (for client viewing candidates)
    applications = TaskApplicationSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'service_category',
            'budget', 'final_price', 'location', 'preferred_time', 'preferredTime',
            'latitude', 'longitude', 'status', 'status_display', 'is_urgent', 
            'requires_materials', 'client_name', 'client_phone', 'createdAt', 
            'applicantsCount', 'assigned_worker_info', 'applications'
        ]
        extra_kwargs = {
            'preferredTime': {'source': 'preferred_time'},
        }
    
    def get_client_name(self, obj):
        """Client full name"""
        user = obj.client
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_assigned_worker_info(self, obj):
        """Complete assigned worker information"""
        if obj.assigned_worker:
            return {
                'id': obj.assigned_worker.id,
                'name': self.get_worker_name(obj.assigned_worker),
                'phone': obj.assigned_worker.phone,
                'rating': float(obj.assigned_worker.average_rating),
                'completed_jobs': obj.assigned_worker.total_jobs_completed,
                'is_online': obj.assigned_worker.is_online,
                'profile_image': obj.assigned_worker.profile_image.url if obj.assigned_worker.profile_image else None,
            }
        return None
    
    def get_worker_name(self, worker):
        """Helper to get worker name"""
        user = worker
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """
    Create/Update service request serializer
    محول إنشاء/تحديث طلب الخدمة
    """
    service_category_id = serializers.IntegerField(write_only=True)
    serviceType = serializers.CharField(write_only=True, required=False)
    preferredTime = serializers.CharField(source='preferred_time', required=False)
    
    # Location fields - either text or coordinates
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'title', 'description', 'serviceType', 'service_category_id',
            'budget', 'location', 'latitude', 'longitude', 
            'preferred_time', 'preferredTime', 'is_urgent', 'requires_materials'
        ]
    
    def validate_service_category_id(self, value):
        """Validate service category exists"""
        from services.models import ServiceCategory
        try:
            ServiceCategory.objects.get(id=value, is_active=True)
            return value
        except ServiceCategory.DoesNotExist:
            raise serializers.ValidationError("Service category not found or inactive")
    
    def validate_budget(self, value):
        """Validate budget - no restrictions, any amount allowed"""
        if value <= 0:
            raise serializers.ValidationError("Le budget doit être supérieur à 0")
        return value
    
    def validate_location(self, value):
        """Validate location text"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("La localisation doit contenir au moins 3 caractères")
        return value.strip()
    
    def validate_preferred_time(self, value):
        """Validate preferred time format"""
        import re
        time_patterns = [
            r'^\d{1,2}:\d{2}\s?(AM|PM|am|pm)$',
            r'^\d{1,2}\s?(AM|PM|am|pm)$',
            r'^\d{1,2}:\d{2}$',
            r'^(Matin|Après-midi|Soir|matin|après-midi|soir)$',
            r'^(Morning|Afternoon|Evening|morning|afternoon|evening)$',
            r'.*'
        ]
        for pattern in time_patterns:
            if re.match(pattern, value.strip()):
                return value.strip()
        return value.strip()
    
    def validate(self, data):
        """Cross-field validation"""
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if (latitude is not None and longitude is None) or (longitude is not None and latitude is None):
            raise serializers.ValidationError("Les coordonnées latitude et longitude doivent être fournies ensemble")
        return data
    
    def validate_title(self, value):
        """Validate title length"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Le titre doit contenir au moins 5 caractères")
        return value.strip()
    
    def validate_description(self, value):
        """Validate description length"""
        if len(value.strip()) < 20:
            raise serializers.ValidationError("La description doit contenir au moins 20 caractères")
        return value.strip()
    
    def create(self, validated_data):
        """Create service request with client from request context"""
        request = self.context['request']
        client = request.user
        
        # Handle serviceType field (convert to service_category_id)
        service_type = validated_data.pop('serviceType', None)
        if service_type and 'service_category_id' not in validated_data:
            from services.models import ServiceCategory
            try:
                category = ServiceCategory.objects.get(name=service_type, is_active=True)
                validated_data['service_category_id'] = category.id
            except ServiceCategory.DoesNotExist:
                pass
        
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        
        service_request = ServiceRequest.objects.create(
            client=client,
            **validated_data
        )
        
        if latitude and longitude:
            service_request.latitude = latitude
            service_request.longitude = longitude
            service_request.save()
        
        return service_request


class AvailableTaskSerializer(serializers.ModelSerializer):
    """
    Available tasks for workers to view and apply
    المهام المتاحة للعمال للعرض والتقدم
    """
    client_name = serializers.SerializerMethodField()
    client_rating = serializers.SerializerMethodField()
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    category = serializers.CharField(source='service_category.name', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    distance = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'category',
            'budget', 'location', 'preferred_time', 'is_urgent',
            'requires_materials', 'createdAt', 'applicantsCount',
            'client_name', 'client_rating', 'distance',
            'has_applied', 'application_status'
        ]
    
    def get_client_name(self, obj):
        """Client name (first name only for privacy)"""
        user = obj.client
        if user.first_name:
            return user.first_name
        return user.username[:3] + "***"
    
    def get_client_rating(self, obj):
        """Client average rating (mock for now)"""
        return 4.5
    
    def get_distance(self, obj):
        """Distance from worker location (mock for now)"""
        import random
        return f"{random.uniform(0.5, 10.0):.1f} km"
    
    def get_has_applied(self, obj):
        """Check if current worker has applied"""
        request = self.context.get('request')
        if request:
            try:
                worker = request.user
                return obj.applications.filter(
                    worker=worker,
                    is_active=True
                ).exists()
            except:
                pass
        return False
    
    def get_application_status(self, obj):
        """Current worker's application status"""
        request = self.context.get('request')
        if request:
            try:
                worker = request.user
                application = obj.applications.filter(
                    worker=worker,
                    is_active=True
                ).first()
                return application.application_status if application else None
            except:
                pass
        return None


class TaskApplicationCreateSerializer(serializers.ModelSerializer):
   """
   Create task application serializer (simplified)
   محول إنشاء تقدم للمهمة (مبسط)
   """
   class Meta:
       model = TaskApplication
       fields = ['application_message']
       extra_kwargs = {
           'application_message': {'required': False, 'allow_blank': True}
       }
   
   def create(self, validated_data):
       """Create application with worker and service request from validated_data"""
       service_request = validated_data.pop('service_request')
       worker = validated_data.pop('worker')
       
       if not validated_data.get('application_message'):
           import random
           validated_data['application_message'] = random.choice(
               TaskApplication.MESSAGE_TEMPLATES
           )
       
       return TaskApplication.objects.create(
           service_request=service_request,
           worker=worker,
           **validated_data
       )

class TaskReviewSerializer(serializers.ModelSerializer):
    """
    Task review serializer (simplified - rating and review text only)
    محول تقييم المهمة (مبسط - تقييم ومراجعة نصية فقط)
    """
    client_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()
    task_title = serializers.CharField(source='service_request.title', read_only=True)
    
    class Meta:
        model = TaskReview
        fields = [
            'id', 'rating', 'review_text', 'client_name', 
            'worker_name', 'task_title', 'created_at'
        ]
        extra_kwargs = {
            'review_text': {'required': False, 'allow_blank': True}
        }
    
    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("La note doit être entre 1 et 5 étoiles")
        return value
    
    def get_client_name(self, obj):
        """Client name"""
        user = obj.client
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username
    
    def get_worker_name(self, obj):
        """Worker name"""
        user = obj.worker
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username


class TaskNotificationSerializer(serializers.ModelSerializer):
    """
    Task notification serializer
    محول إشعارات المهام
    """
    class Meta:
        model = TaskNotification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'is_read', 'created_at', 'read_at'
        ]
