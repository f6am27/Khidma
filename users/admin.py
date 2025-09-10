# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, AdminProfile, WorkerProfile, ClientProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """إدارة المستخدمين المخصصة"""
    
    list_display = [
        'display_identifier', 'get_full_name', 'role', 
        'is_verified', 'onboarding_completed', 'is_active', 'created_at'
    ]
    list_filter = ['role', 'is_verified', 'onboarding_completed', 'is_active', 'created_at']
    search_fields = ['phone', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    # حقول التحرير
    fieldsets = (
        (None, {
            'fields': ('phone', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'role')
        }),
        ('Status', {
            'fields': ('is_verified', 'onboarding_completed', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    def display_identifier(self, obj):
        """عرض المعرف (phone أو email)"""
        if obj.role == 'admin':
            return obj.email or 'No Email'
        return obj.phone or 'No Phone'
    display_identifier.short_description = 'Identifier'
    
    def get_full_name(self, obj):
        """الاسم الكامل"""
        return obj.get_full_name() or 'No Name'
    get_full_name.short_description = 'Full Name'


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """إدارة ملفات الأدمن"""
    
    list_display = [
        'display_name', 'user_email', 'department', 
        'is_active_admin', 'last_login_dashboard', 'created_at'
    ]
    list_filter = ['is_active_admin', 'department', 'created_at']
    search_fields = ['display_name', 'user__email', 'department']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'display_name', 'bio')
        }),
        ('Profile', {
            'fields': ('profile_image', 'department')
        }),
        ('Status', {
            'fields': ('is_active_admin', 'last_login_dashboard')
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    """إدارة ملفات العمال"""
    
    list_display = [
        'worker_name', 'service_category', 'service_area', 
        'base_price', 'average_rating', 'total_jobs_completed', 
        'is_verified', 'is_available', 'created_at'
    ]
    list_filter = [
        'service_category', 'is_verified', 'is_available', 
        'is_online', 'created_at'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__phone',
        'service_category', 'service_area', 'bio'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Service Info', {
            'fields': ('service_category', 'bio', 'service_area', 'base_price')
        }),
        ('Availability', {
            'fields': ('available_days', 'work_start_time', 'work_end_time')
        }),
        ('Profile', {
            'fields': ('profile_image',)
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_jobs_completed', 'average_rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_verified', 'is_available', 'is_online')
        }),
    )
    
    readonly_fields = ['total_jobs_completed', 'average_rating', 'total_reviews']
    
    def worker_name(self, obj):
        return obj.user.get_full_name() or obj.user.phone
    worker_name.short_description = 'Worker Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """إدارة ملفات العملاء"""
    
    list_display = [
        'client_name', 'user_phone', 'address_short', 
        'total_tasks_published', 'total_tasks_completed', 
        'success_rate_display', 'total_amount_spent', 'created_at'
    ]
    list_filter = ['gender', 'preferred_language', 'notifications_enabled', 'created_at']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__phone',
        'bio', 'address'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Personal Info', {
            'fields': ('bio', 'date_of_birth', 'gender')
        }),
        ('Contact Info', {
            'fields': ('address', 'emergency_contact')
        }),
        ('Profile', {
            'fields': ('profile_image',)
        }),
        ('Statistics', {
            'fields': ('total_tasks_published', 'total_tasks_completed', 'total_amount_spent'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'notifications_enabled'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_tasks_published', 'total_tasks_completed', 'total_amount_spent']
    
    def client_name(self, obj):
        return obj.user.get_full_name() or obj.user.phone
    client_name.short_description = 'Client Name'
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = 'Phone'
    
    def address_short(self, obj):
        if obj.address:
            return obj.address[:50] + '...' if len(obj.address) > 50 else obj.address
        return 'No Address'
    address_short.short_description = 'Address'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 80 else 'orange' if rate >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')