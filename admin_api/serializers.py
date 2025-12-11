# admin_api/serializers.py
from rest_framework import serializers
from users.models import User, AdminProfile,WorkerProfile, ClientProfile
from tasks.models import ServiceRequest, TaskApplication, TaskReview
# from payments.models import Payment
from chat.models import Report, Conversation, Message
from services.models import ServiceCategory, NouakchottArea
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from complaints.models import Complaint

# ==================== Dashboard Statistics ====================
class DashboardStatsSerializer(serializers.Serializer):    
    # Users Stats
    total_users = serializers.IntegerField()
    total_clients = serializers.IntegerField()
    total_workers = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    
    # Tasks Stats
    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    cancelled_tasks = serializers.IntegerField()
    
    # Financial Stats
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_task_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Reports Stats
    pending_reports = serializers.IntegerField()
    resolved_reports = serializers.IntegerField()

    # ✅✅✅ Complaints Stats - فقط التعريفات ✅✅✅
    total_complaints = serializers.IntegerField()
    new_complaints = serializers.IntegerField()
    pending_complaints = serializers.IntegerField()
    # ✅✅✅ نهاية ✅✅✅
    
    # Growth Stats
    user_growth_rate = serializers.FloatField()
    task_completion_rate = serializers.FloatField()


# ==================== User Management ====================
class AdminUserListSerializer(serializers.ModelSerializer):
    """قائمة المستخدمين للأدمن"""
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField() 
    status = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    suspension_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_verified', 'is_active', 'is_suspended',
            'onboarding_completed', 'status', 'total_tasks',
            'suspension_info', 'date_joined', 'last_login','profile_image_url'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone or obj.email
    
    def get_profile_image_url(self, obj):
        """جلب صورة البروفايل"""
        try:
            if obj.role == 'client' and hasattr(obj, 'client_profile'):
                profile = obj.client_profile
            elif obj.role == 'worker' and hasattr(obj, 'worker_profile'):
                profile = obj.worker_profile
            else:
                return None
            
            if profile and profile.profile_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.profile_image.url)
        except:
            pass
        return None
    
    def get_status(self, obj):
        if obj.is_suspended:
            return 'suspended'
        elif not obj.is_active:
            return 'inactive'
        return 'active'
    
    def get_total_tasks(self, obj):
        if obj.role == 'client':
            return ServiceRequest.objects.filter(client=obj).count()
        elif obj.role == 'worker':
            return ServiceRequest.objects.filter(assigned_worker=obj).count()
        return 0
    
    def get_suspension_info(self, obj):
        if obj.is_suspended:
            return {
                'until': obj.suspended_until,
                'reason': obj.suspension_reason
            }
        return None


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """تفاصيل المستخدم للأدمن"""
    full_name = serializers.SerializerMethodField()
    profile_details = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_verified', 'is_active', 'is_suspended',
            'suspended_until', 'suspension_reason', 'onboarding_completed',
            'date_joined', 'last_login', 'created_at', 'updated_at',
            'profile_details', 'statistics'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone or obj.email
    
    def get_profile_details(self, obj):
        """معلومات Profile حسب النوع"""
        if obj.role == 'client':
            try:
                profile = obj.client_profile
                
                # ✅ حساب المهام من ServiceRequest مباشرة
                published_tasks = ServiceRequest.objects.filter(
                    client=obj, 
                    status='published'
                ).count()
                
                active_tasks = ServiceRequest.objects.filter(
                    client=obj, 
                    status='active'
                ).count()
                
                cancelled_tasks = ServiceRequest.objects.filter(
                    client=obj, 
                    status='cancelled'
                ).count()
                
                # ✅ عرض الصورة
                profile_image_url = None
                if profile.profile_image:
                    request = self.context.get('request')
                    if request:
                        profile_image_url = request.build_absolute_uri(profile.profile_image.url)
                
                return {
                    'gender': profile.gender,
                    'address': profile.address,
                    'published_tasks_count': published_tasks,
                    'active_tasks_count': active_tasks,
                    'cancelled_tasks_count': cancelled_tasks,
                    'profile_image_url': profile_image_url,
                }
            except:
                return {
                    'published_tasks_count': 0,
                    'active_tasks_count': 0,
                    'cancelled_tasks_count': 0,
                }
        
        elif obj.role == 'worker':
            try:
                profile = obj.worker_profile
                
                # ✅ عدد المهام المقبولة من UserTaskCounter
                try:
                    from payments.models import UserTaskCounter
                    counter = UserTaskCounter.objects.get(user=obj)
                    accepted_tasks = counter.accepted_tasks_count
                except:
                    accepted_tasks = 0
                
                # ✅ عرض الصورة
                profile_image_url = None
                if profile.profile_image:
                    request = self.context.get('request')
                    if request:
                        profile_image_url = request.build_absolute_uri(profile.profile_image.url)
                
                return {
                    'service_category': profile.service_category,
                    'service_area': profile.service_area,
                    'average_rating': float(profile.average_rating or 0),
                    'total_reviews': profile.total_reviews,
                    'accepted_tasks_count': accepted_tasks,  # ✅ الاسم الجديد
                    'is_online': profile.is_online,
                    'location_sharing_enabled': profile.location_sharing_enabled,
                    'location_status': profile.location_status,
                    'current_latitude': str(profile.current_latitude) if profile.current_latitude else None,
                    'current_longitude': str(profile.current_longitude) if profile.current_longitude else None,
                    'location_accuracy': profile.location_accuracy,
                    'location_last_updated': profile.location_last_updated,
                    'profile_image_url': profile_image_url,
                }
            except Exception as e:
                print(f"❌ Error loading worker profile: {e}")
                return {
                    'accepted_tasks_count': 0,
                    'average_rating': 0,
                    'total_reviews': 0,
                }
        
        return None

    def get_statistics(self, obj):
        if obj.role == 'client':
            tasks = ServiceRequest.objects.filter(client=obj)
            return {
                'total_tasks': tasks.count(),
                'completed_tasks': tasks.filter(status='completed').count(),
                'cancelled_tasks': tasks.filter(status='cancelled').count(),
                'total_spent': 0  # ❌ معطل مؤقتاً
            }
        elif obj.role == 'worker':
            tasks = ServiceRequest.objects.filter(assigned_worker=obj)
            return {
                'total_jobs': tasks.count(),
                'completed_jobs': tasks.filter(status='completed').count(),
                'total_earned': 0,  # ❌ معطل مؤقتاً
                'average_rating': float(obj.worker_profile.average_rating) if hasattr(obj, 'worker_profile') else 0
            }
        return {}

class UserSuspensionSerializer(serializers.Serializer):
    """تعليق/إلغاء تعليق المستخدم"""
    days = serializers.IntegerField(required=False, min_value=1, max_value=365)
    reason = serializers.CharField(required=False, allow_blank=True)
    permanent = serializers.BooleanField(default=False)


# ==================== Reports Management ====================
class AdminReportListSerializer(serializers.ModelSerializer):
    """قائمة البلاغات للأدمن"""
    reporter_name = serializers.SerializerMethodField()
    reported_user_name = serializers.SerializerMethodField()
    reported_user_reports_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'reporter', 'reporter_name', 'reported_user',
            'reported_user_name', 'reported_user_reports_count',
            'reason', 'description', 'status', 'created_at',
            'resolved_at', 'admin_notes'
        ]
    
    def get_reporter_name(self, obj):
        return obj.reporter.get_full_name() or obj.reporter.phone
    
    def get_reported_user_name(self, obj):
        return obj.reported_user.get_full_name() or obj.reported_user.phone
    
    def get_reported_user_reports_count(self, obj):
        return Report.objects.filter(reported_user=obj.reported_user).count()


class ReportActionSerializer(serializers.Serializer):
    """إجراءات البلاغات"""
    action = serializers.ChoiceField(choices=[
        'resolve', 'dismiss', 'suspend_3days', 'suspend_7days',
        'suspend_30days', 'permanent_ban'
    ])
    admin_notes = serializers.CharField(required=False, allow_blank=True)


# ==================== Categories & Areas Management ====================
class AdminCategorySerializer(serializers.ModelSerializer):
    """إدارة الفئات"""
    workers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCategory
        fields = '__all__'
    
    def get_workers_count(self, obj):
        return User.objects.filter(
            role='worker',
            worker_profile__service_category=obj.name
        ).count()


class AdminAreaSerializer(serializers.ModelSerializer):
    """إدارة المناطق"""
    workers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = NouakchottArea
        fields = '__all__'
    
    def get_workers_count(self, obj):
        return User.objects.filter(
            role='worker',
            worker_profile__service_area__icontains=obj.name
        ).count()


# ==================== Financial Reports ====================
class FinancialSummarySerializer(serializers.Serializer):
    """ملخص مالي"""
    total_transactions = serializers.IntegerField()
    completed_transactions = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_last_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_transaction_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_earning_workers = serializers.ListField()
    revenue_by_category = serializers.DictField()



class AdminProfileUpdateSerializer(serializers.Serializer):
    """
    تحديث بيانات الأدمن - كل الحقول اختيارية
    """
    # حقول من User
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    
    # حقول من AdminProfile
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_email(self, value):
        """التحقق من أن الإيميل غير مستخدم من قبل أدمن آخر"""
        user = self.context['request'].user
        
        if User.objects.filter(email=value, role='admin').exclude(id=user.id).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé par un autre administrateur")
        
        return value
    
    def update(self, instance, validated_data):
        """تحديث البيانات"""
        user = instance
        
        # تحديث حقول User
        if 'first_name' in validated_data:
            user.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            user.last_name = validated_data['last_name']
        if 'email' in validated_data:
            user.email = validated_data['email']
        
        user.save()
        
        # تحديث حقول AdminProfile
        admin_profile, created = AdminProfile.objects.get_or_create(user=user)
        
        if 'display_name' in validated_data:
            admin_profile.display_name = validated_data['display_name']
        if 'bio' in validated_data:
            admin_profile.bio = validated_data['bio']
        if 'department' in validated_data:
            admin_profile.department = validated_data['department']
        
        admin_profile.save()
        
        return user


class AdminProfileSerializer(serializers.Serializer):
    """
    عرض بيانات الأدمن كاملة
    """
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    bio = serializers.CharField(read_only=True)
    department = serializers.CharField(read_only=True)
    profile_image = serializers.SerializerMethodField()
    is_online = serializers.BooleanField(read_only=True)
    last_activity = serializers.DateTimeField(read_only=True)
    
    def get_profile_image(self, obj):
        """الحصول على رابط الصورة"""
        if hasattr(obj, 'admin_profile') and obj.admin_profile and obj.admin_profile.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.admin_profile.profile_image.url)
        return None
    

class AdminChangePasswordSerializer(serializers.Serializer):
    """
    تغيير كلمة المرور للأدمن
    """
    old_password = serializers.CharField(
        min_length=6, 
        max_length=128, 
        write_only=True,
        error_messages={
            'required': 'Mot de passe actuel requis',
            'min_length': 'Le mot de passe doit contenir au moins 6 caractères'
        }
    )
    new_password = serializers.CharField(
        min_length=6, 
        max_length=128, 
        write_only=True,
        error_messages={
            'required': 'Nouveau mot de passe requis',
            'min_length': 'Le mot de passe doit contenir au moins 6 caractères'
        }
    )
    new_password_confirm = serializers.CharField(
        min_length=6, 
        max_length=128, 
        write_only=True,
        error_messages={
            'required': 'Confirmation du mot de passe requise',
            'min_length': 'Le mot de passe doit contenir au moins 6 caractères'
        }
    )

    def validate_old_password(self, value):
        """التحقق من صحة كلمة المرور القديمة"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect")
        return value

    def validate(self, attrs):
        """التحقق من تطابق كلمات المرور الجديدة"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "Les mots de passe ne correspondent pas"
            })
        
        # التحقق من أن كلمة المرور الجديدة مختلفة عن القديمة
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                "new_password": "Le nouveau mot de passe doit être différent de l'ancien"
            })
        
        return attrs
    
class AdminPasswordResetRequestSerializer(serializers.Serializer):
    """
    طلب إعادة تعيين كلمة المرور
    """
    email = serializers.EmailField(
        error_messages={
            'required': 'Email requis',
            'invalid': 'Email invalide'
        }
    )
    language = serializers.ChoiceField(
        choices=['fr', 'ar', 'en'],
        default='fr',
        required=False
    )
    
    def validate_email(self, value):
        """التحقق من وجود الأدمن"""
        try:
            user = User.objects.get(email=value, role='admin')
            if not user.is_active:
                raise serializers.ValidationError("Compte désactivé")
        except User.DoesNotExist:
            raise serializers.ValidationError("Aucun administrateur avec cet email")
        
        return value


class AdminPasswordResetConfirmSerializer(serializers.Serializer):
    """
    تأكيد إعادة التعيين بـ OTP
    """
    email = serializers.EmailField()
    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        error_messages={
            'required': 'Code OTP requis',
            'min_length': 'Le code doit contenir 6 chiffres',
            'max_length': 'Le code doit contenir 6 chiffres'
        }
    )
    new_password = serializers.CharField(
        min_length=6,
        max_length=128,
        write_only=True,
        error_messages={
            'required': 'Nouveau mot de passe requis',
            'min_length': 'Le mot de passe doit contenir au moins 6 caractères'
        }
    )
    new_password_confirm = serializers.CharField(
        min_length=6,
        max_length=128,
        write_only=True,
        error_messages={
            'required': 'Confirmation requise'
        }
    )
    
    def validate(self, attrs):
        """التحقق من تطابق كلمات المرور"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "Les mots de passe ne correspondent pas"
            })
        return attrs
    
# ✅ 1. Top Rated Users
class TopRatedUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    phone = serializers.CharField()
    role = serializers.CharField()
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    total_jobs_completed = serializers.IntegerField()
    date_joined = serializers.DateTimeField()
    profile_image_url = serializers.CharField(allow_null=True)

# ✅ 2. Most Reported Users
class MostReportedUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    phone = serializers.CharField()
    role = serializers.CharField()
    total_reports = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    resolved_reports = serializers.IntegerField()
    dismissed_reports = serializers.IntegerField()
    last_report_date = serializers.DateTimeField(allow_null=True)
    is_suspended = serializers.BooleanField()
    suspension_reason = serializers.CharField(allow_null=True)

# ✅ 3. Subscription Analytics
class SubscriptionAnalyticsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    premium_users = serializers.IntegerField()
    free_users = serializers.IntegerField()
    users_at_4_tasks = serializers.IntegerField()  # Warning zone
    users_at_5_tasks = serializers.IntegerField()  # Limit reached
    conversion_rate = serializers.FloatField()
    monthly_revenue_potential = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Breakdown by role
    premium_clients = serializers.IntegerField()
    premium_workers = serializers.IntegerField()
    free_clients = serializers.IntegerField()
    free_workers = serializers.IntegerField()

# ✅ 4. Platform Activity
class PlatformActivitySerializer(serializers.Serializer):
    # Task stats
    tasks_published_today = serializers.IntegerField()
    tasks_published_this_week = serializers.IntegerField()
    tasks_published_this_month = serializers.IntegerField()
    
    # Acceptance stats
    tasks_accepted_today = serializers.IntegerField()
    tasks_accepted_this_week = serializers.IntegerField()
    tasks_accepted_this_month = serializers.IntegerField()
    acceptance_rate = serializers.FloatField()
    
    # Cancellation stats
    tasks_cancelled_today = serializers.IntegerField()
    tasks_cancelled_this_week = serializers.IntegerField()
    tasks_cancelled_this_month = serializers.IntegerField()
    cancellation_rate = serializers.FloatField()
    
    # Active workers
    workers_online_now = serializers.IntegerField()
    workers_with_active_location = serializers.IntegerField()

# ✅ 5. Top Service Categories
class TopServiceCategorySerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    category_name = serializers.CharField()
    category_icon = serializers.CharField()
    total_tasks = serializers.IntegerField()
    total_workers = serializers.IntegerField()
    average_budget = serializers.DecimalField(max_digits=10, decimal_places=2)
    tasks_this_month = serializers.IntegerField()

# ✅ 6. Most Active Users
class MostActiveUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    phone = serializers.CharField()
    role = serializers.CharField()
    
    # For clients
    tasks_published = serializers.IntegerField(allow_null=True)
    tasks_accepted = serializers.IntegerField(allow_null=True)
    
    # For workers
    applications_sent = serializers.IntegerField(allow_null=True)
    tasks_completed = serializers.IntegerField(allow_null=True)
    
    last_activity = serializers.DateTimeField()
    is_online = serializers.BooleanField()

# ✅ 7. Cancellation Analytics
class CancellationAnalyticsSerializer(serializers.Serializer):
    total_tasks = serializers.IntegerField()
    cancelled_tasks = serializers.IntegerField()
    cancellation_rate = serializers.FloatField()
    
    # Top cancellers (clients)
    top_cancellers = serializers.ListField()
    
    # Cancellation trends
    cancelled_today = serializers.IntegerField()
    cancelled_this_week = serializers.IntegerField()
    cancelled_this_month = serializers.IntegerField()

