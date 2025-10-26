# tasks/serializers.py
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification
from users.models import User
from services.serializers import ServiceCategorySerializer
from notifications.utils import notify_new_task_available

# --------------------------------------------------
# معلومات أساسية للمستخدم
# --------------------------------------------------
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'date_joined']

# --------------------------------------------------
# محول طلبات التقدم للمهمة
# --------------------------------------------------
class TaskApplicationSerializer(serializers.ModelSerializer):
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    completedJobs = serializers.SerializerMethodField()
    isOnline = serializers.SerializerMethodField()
    profileImage = serializers.CharField(source='worker.profile_image', read_only=True)
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
        user = obj.worker
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username

    def get_rating(self, obj):
        worker = obj.worker
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            return float(worker.worker_profile.average_rating) if worker.worker_profile.average_rating else 0.0
        return 0.0
    
    def get_reviewCount(self, obj):
        worker = obj.worker
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            return worker.worker_profile.total_reviews or 0
        return 0
    
    def get_completedJobs(self, obj):
        worker = obj.worker
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            return worker.worker_profile.total_jobs_completed or 0
        return 0
    
    def get_isOnline(self, obj):
        worker = obj.worker
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            return worker.worker_profile.is_online
        return False

    def get_location(self, obj):
        worker = obj.worker
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            area = worker.worker_profile.service_area.split(',')[0].strip() if worker.worker_profile.service_area else "Unknown"
        else:
            area = "Unknown"
        import random
        distance = random.uniform(0.5, 5.0)
        return f"{area}, {distance:.1f}km"

# --------------------------------------------------
# قائمة طلبات الخدمة (لواجهة Flutter)
# --------------------------------------------------
class ServiceRequestListSerializer(serializers.ModelSerializer):
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    status = serializers.CharField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    assignedProvider = serializers.SerializerMethodField()
    providerRating = serializers.SerializerMethodField()
    isUrgent = serializers.BooleanField(source='is_urgent', read_only=True)  
    timeDescription = serializers.CharField(source='time_description', read_only=True, allow_null=True, required=False)  
    workStartedAt = serializers.DateTimeField(source='work_started_at', read_only=True, allow_null=True) 
    finalPrice = serializers.DecimalField(source='final_price', max_digits=10, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'budget', 'finalPrice',
            'location', 'preferredTime', 'status', 'createdAt',
            'applicantsCount', 'assignedProvider', 'providerRating',
            'isUrgent', 'timeDescription' , 'workStartedAt' 
        ]
        extra_kwargs = {'preferredTime': {'source': 'preferred_time'}}

    def get_assignedProvider(self, obj):
        if obj.assigned_worker:
            user = obj.assigned_worker
            if hasattr(user, 'first_name') and user.first_name and hasattr(user, 'last_name') and user.last_name:
                return f"{user.first_name} {user.last_name}"
            if hasattr(user, 'username') and user.username:
                return user.username
            if hasattr(user, 'phone') and user.phone:
                return user.phone
            return "Worker"
        return None

    def get_providerRating(self, obj):
        if obj.assigned_worker:
            if hasattr(obj.assigned_worker, 'worker_profile') and obj.assigned_worker.worker_profile:
                return int(obj.assigned_worker.worker_profile.average_rating) if obj.assigned_worker.worker_profile.average_rating else 0
        return None

# --------------------------------------------------
# تفاصيل طلب الخدمة
# --------------------------------------------------
class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    service_category = ServiceCategorySerializer(read_only=True)
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    assigned_worker_info = serializers.SerializerMethodField()
    applications = TaskApplicationSerializer(many=True, read_only=True)
    has_exact_coordinates = serializers.SerializerMethodField()
    location_type = serializers.SerializerMethodField()
    distance_from_worker = serializers.SerializerMethodField()
    finalPrice = serializers.DecimalField(source='final_price', max_digits=10, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'service_category',
            'budget', 'final_price', 'finalPrice', 'location', 'preferred_time', 'preferredTime',
            'latitude', 'longitude', 'status', 'status_display', 'is_urgent', 
            'requires_materials', 'client_name', 'client_phone', 'createdAt', 
            'applicantsCount', 'assigned_worker_info', 'applications',
            'has_exact_coordinates', 'location_type', 'distance_from_worker'
        ]
        extra_kwargs = {'preferredTime': {'source': 'preferred_time'}}

    def get_client_name(self, obj):
        user = obj.client
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username

    def get_assigned_worker_info(self, obj):
        if obj.assigned_worker:
            worker = obj.assigned_worker
            if hasattr(worker, 'worker_profile') and worker.worker_profile:
                rating = float(worker.worker_profile.average_rating) if worker.worker_profile.average_rating else 0.0
                completed_jobs = worker.worker_profile.total_jobs_completed or 0
                is_online = worker.worker_profile.is_online
            else:
                rating = 0.0
                completed_jobs = 0
                is_online = False
            
            return {
                'id': worker.id,
                'name': self.get_worker_name(worker),
                'phone': worker.phone,
                'rating': rating,
                'completed_jobs': completed_jobs,
                'is_online': is_online,
                'profile_image': worker.worker_profile.profile_image.url if (hasattr(worker, 'worker_profile') and worker.worker_profile and worker.worker_profile.profile_image) else None,
            }
        return None

    def get_worker_name(self, worker):
        if worker.first_name and worker.last_name:
            return f"{worker.first_name} {worker.last_name}"
        return worker.username

    def get_has_exact_coordinates(self, obj):
        return bool(obj.latitude and obj.longitude)

    def get_location_type(self, obj):
        if obj.latitude and obj.longitude:
            return 'exact_coordinates'
        return 'area_only'

    def get_distance_from_worker(self, obj):
        request = self.context.get('request')
        if not request or request.user.role != 'worker':
            return None
        if not (obj.latitude and obj.longitude):
            return None
        if not (hasattr(request.user, 'worker_profile') and
                request.user.worker_profile.current_latitude and
                request.user.worker_profile.current_longitude):
            return None
        worker_profile = request.user.worker_profile
        distance = worker_profile.calculate_distance_to(
            float(obj.latitude),
            float(obj.longitude)
        )
        return round(distance, 1) if distance else None

# --------------------------------------------------
# إنشاء/تحديث طلب الخدمة مع دعم الموقع المحسن
# --------------------------------------------------
class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    service_category_id = serializers.IntegerField(write_only=True)
    serviceType = serializers.CharField(write_only=True, required=False)
    preferredTime = serializers.CharField(source='preferred_time', required=False)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True, help_text="خط العرض")
    longitude = serializers.DecimalField(max_digits=11, decimal_places=7, required=False, allow_null=True, help_text="خط الطول")
    location_method = serializers.ChoiceField(
        choices=[('current_location', 'الموقع الحالي'), ('select_area', 'اختيار منطقة')],
        write_only=True, required=False, help_text="طريقة تحديد الموقع"
    )
    area_id = serializers.IntegerField(write_only=True, required=False, allow_null=True, help_text="معرف المنطقة")

    class Meta:
        model = ServiceRequest
        fields = [
            'title', 'description', 'serviceType', 'service_category_id',
            'budget', 'location', 'latitude', 'longitude', 
            'preferred_time', 'preferredTime', 'is_urgent', 'requires_materials',
            'location_method', 'area_id'
        ]

    def validate(self, data):
        location_method = data.get('location_method', 'select_area')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        area_id = data.get('area_id')
        location = data.get('location')

        if location_method == 'current_location':
            if latitude is None or longitude is None:
                raise serializers.ValidationError({'location': 'يجب تقديم إحداثيات الموقع الحالي'})
            if not (-90 <= float(latitude) <= 90):
                raise serializers.ValidationError({'latitude': 'خط العرض يجب أن يكون بين -90 و 90'})
            if not (-180 <= float(longitude) <= 180):
                raise serializers.ValidationError({'longitude': 'خط الطول يجب أن يكون بين -180 و 180'})
        elif location_method == 'select_area':
            if area_id:
                from services.models import NouakchottArea
                try:
                    area = NouakchottArea.objects.get(id=area_id, is_active=True)
                    data['location'] = f"{area.name}, Nouakchott"
                except NouakchottArea.DoesNotExist:
                    raise serializers.ValidationError({'area_id': 'المنطقة المحددة غير موجودة أو غير نشطة'})
            elif not location:
                raise serializers.ValidationError({'location': 'يجب تحديد موقع المهمة أو اختيار منطقة'})
        return data
    
    def create(self, validated_data):
        request = self.context['request']
        client = request.user
        location_method = validated_data.pop('location_method', 'select_area')
        area_id = validated_data.pop('area_id', None)
        service_type = validated_data.pop('serviceType', None)
        
        time_desc = request.data.get('timeDescription') or request.data.get('time_description')

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
        
        if time_desc:
            service_request.time_description = time_desc
        
        service_request.save()

        self._notify_relevant_workers(service_request, location_method)

        return service_request
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        
        if request and 'service_category_id' in request.data:
            category_id = request.data.get('service_category_id')
            if category_id:
                instance.service_category_id = category_id
        
        if request:
            time_desc = request.data.get('timeDescription') or request.data.get('time_description')
            if time_desc:
                instance.time_description = time_desc
        
        validated_data.pop('location_method', None)
        validated_data.pop('area_id', None)
        validated_data.pop('serviceType', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

    def _notify_relevant_workers(self, task, location_method):
        from users.models import User
        relevant_workers = User.objects.filter(
            role='worker',
            is_verified=True,
            onboarding_completed=True,
            worker_profile__is_available=True,
            worker_services__category=task.service_category
        ).distinct()

        if task.latitude and task.longitude and location_method == 'current_location':
            nearby_workers = []
            for worker in relevant_workers:
                if hasattr(worker, 'worker_profile') and worker.worker_profile.location_sharing_enabled and \
                   worker.worker_profile.current_latitude and worker.worker_profile.current_longitude:
                    distance = worker.worker_profile.calculate_distance_to(
                        float(task.latitude), float(task.longitude)
                    )
                    if distance and distance <= 30:
                        nearby_workers.append(worker)
            workers_to_notify = nearby_workers[:20]
        else:
            area_name = task.location.split(',')[0].strip()
            area_workers = relevant_workers.filter(
                worker_profile__service_area__icontains=area_name
            )[:15]
            workers_to_notify = list(area_workers)

    # ✅ إرسال إشعارات مع Firebase
        notifications_sent = 0
        for worker in workers_to_notify:
            try:
                result = notify_new_task_available(
                    worker_user=worker,
                    task=task
                )
                if result.get('success'):
                    notifications_sent += 1
            except Exception as e:
                print(f"❌ Failed to notify worker {worker.id}: {e}")
        
        print(f"📢 Notified {notifications_sent}/{len(workers_to_notify)} workers")
        return notifications_sent

# --------------------------------------------------
# محول المهام المتاحة للعمال
# --------------------------------------------------
class AvailableTaskSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_rating = serializers.SerializerMethodField()
    serviceType = serializers.CharField(source='service_category.name', read_only=True)
    category = serializers.CharField(source='service_category.name', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    applicantsCount = serializers.IntegerField(source='applications_count', read_only=True)
    distance_from_worker = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'serviceType', 'category',
            'budget', 'location', 'preferred_time', 'is_urgent',
            'requires_materials', 'createdAt', 'applicantsCount',
            'client_name', 'client_rating', 'distance_from_worker',
            'has_applied', 'application_status',
            'latitude', 'longitude'
        ]

    def get_client_name(self, obj):
        user = obj.client
        if user.first_name:
            return user.first_name
        return user.username[:3] + "***"

    def get_client_rating(self, obj):
        return 4.5

    def get_distance_from_worker(self, obj):
        request = self.context.get('request')
        if not request or request.user.role != 'worker':
            return None
        if not (hasattr(request.user, 'worker_profile') and
                request.user.worker_profile.current_latitude and
                request.user.worker_profile.current_longitude):
            return None
        worker_profile = request.user.worker_profile
        if obj.latitude and obj.longitude:
            distance = worker_profile.calculate_distance_to(
                float(obj.latitude), float(obj.longitude)
            )
            return round(distance, 1) if distance else None
        return None

    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request:
            worker = request.user
            return obj.applications.filter(worker=worker, is_active=True).exists()
        return False

    def get_application_status(self, obj):
        request = self.context.get('request')
        if request:
            worker = request.user
            application = obj.applications.filter(worker=worker, is_active=True).first()
            return application.application_status if application else None
        return None

# --------------------------------------------------
# إنشاء تقدم للمهمة
# --------------------------------------------------
class TaskApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskApplication
        fields = ['application_message']
        extra_kwargs = {'application_message': {'required': False, 'allow_blank': True}}

    def create(self, validated_data):
        service_request = validated_data.pop('service_request')
        worker = validated_data.pop('worker')
        if not validated_data.get('application_message'):
            import random
            validated_data['application_message'] = random.choice(TaskApplication.MESSAGE_TEMPLATES)
        return TaskApplication.objects.create(
            service_request=service_request,
            worker=worker,
            **validated_data
        )

# --------------------------------------------------
# تقييم المهام
# --------------------------------------------------
class TaskReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()
    task_title = serializers.CharField(source='service_request.title', read_only=True)

    class Meta:
        model = TaskReview
        fields = ['id', 'rating', 'review_text', 'client_name', 'worker_name', 'task_title', 'created_at']
        extra_kwargs = {'review_text': {'required': False, 'allow_blank': True}}

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("La note doit être entre 1 et 5 étoiles")
        return value

    def get_client_name(self, obj):
        user = obj.client
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username

    def get_worker_name(self, obj):
        user = obj.worker
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username

# --------------------------------------------------
# إشعارات المهام
# --------------------------------------------------
class TaskNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskNotification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'read_at']


class TaskMapDataSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='service_category.name', read_only=True)
    category_icon = serializers.CharField(source='service_category.icon', read_only=True)
    distance_km = serializers.SerializerMethodField()
    client_initial = serializers.SerializerMethodField()
    urgency_level = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'latitude', 'longitude', 'budget', 
            'is_urgent', 'category', 'category_icon', 'distance_km',
            'client_initial', 'urgency_level', 'created_at', 'requires_materials'
        ]
    
    def get_distance_km(self, obj):
        request = self.context.get('request')
        if not request or request.user.role != 'worker':
            return None
        
        worker_profile = getattr(request.user, 'worker_profile', None)
        if not worker_profile or not worker_profile.current_latitude or not worker_profile.current_longitude:
            return None
        
        if obj.latitude and obj.longitude:
            distance = worker_profile.calculate_distance_to(
                float(obj.latitude), float(obj.longitude)
            )
            return round(distance, 1) if distance else None
        return None
    
    def get_client_initial(self, obj):
        client = obj.client
        if client.first_name:
            return client.first_name[0].upper()
        return client.phone[0] if client.phone else 'C'
    
    def get_urgency_level(self, obj):
        if obj.is_urgent:
            return 'high'
        return 'normal'