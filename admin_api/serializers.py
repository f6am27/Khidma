# admin_api/serializers.py
from rest_framework import serializers
from users.models import User, WorkerProfile, ClientProfile
from tasks.models import ServiceRequest, TaskApplication, TaskReview
from payments.models import Payment
from chat.models import Report, Conversation, Message
from services.models import ServiceCategory, NouakchottArea
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta


# ==================== Dashboard Statistics ====================
class DashboardStatsSerializer(serializers.Serializer):
    """إحصائيات Dashboard الرئيسية"""
    
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
    
    # Growth Stats
    user_growth_rate = serializers.FloatField()
    task_completion_rate = serializers.FloatField()


# ==================== User Management ====================
class AdminUserListSerializer(serializers.ModelSerializer):
    """قائمة المستخدمين للأدمن"""
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    total_tasks = serializers.SerializerMethodField()
    suspension_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_verified', 'is_active', 'is_suspended',
            'onboarding_completed', 'status', 'total_tasks',
            'suspension_info', 'date_joined', 'last_login'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone or obj.email
    
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
        if obj.role == 'client' and hasattr(obj, 'client_profile'):
            profile = obj.client_profile
            return {
                'gender': profile.gender,
                'address': profile.address,
                'total_tasks_published': profile.total_tasks_published,
                'total_tasks_completed': profile.total_tasks_completed,
                'total_amount_spent': str(profile.total_amount_spent)
            }
        elif obj.role == 'worker' and hasattr(obj, 'worker_profile'):
            profile = obj.worker_profile
            return {
                'service_category': profile.service_category,
                'service_area': profile.service_area,
                'base_price': str(profile.base_price),
                'average_rating': float(profile.average_rating),
                'total_jobs_completed': profile.total_jobs_completed,
                'total_reviews': profile.total_reviews
            }
        return None
    
    def get_statistics(self, obj):
        if obj.role == 'client':
            tasks = ServiceRequest.objects.filter(client=obj)
            return {
                'total_tasks': tasks.count(),
                'completed_tasks': tasks.filter(status='completed').count(),
                'cancelled_tasks': tasks.filter(status='cancelled').count(),
                'total_spent': float(Payment.objects.filter(
                    payer=obj, status='completed'
                ).aggregate(Sum('amount'))['amount__sum'] or 0)
            }
        elif obj.role == 'worker':
            tasks = ServiceRequest.objects.filter(assigned_worker=obj)
            return {
                'total_jobs': tasks.count(),
                'completed_jobs': tasks.filter(status='completed').count(),
                'total_earned': float(Payment.objects.filter(
                    receiver=obj, status='completed'
                ).aggregate(Sum('amount'))['amount__sum'] or 0),
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