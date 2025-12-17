from django.contrib import admin
from .models import UserTaskCounter, TaskBundle, PlatformSubscription


@admin.register(UserTaskCounter)
class UserTaskCounterAdmin(admin.ModelAdmin):
    """
    إدارة عدادات المهام - النظام الجديد
    """
    list_display = [
        'id',
        'user',
        'free_tasks_used',
        'total_subscriptions',
        'current_limit',
        'current_usage',
        'tasks_remaining',
        'needs_payment',
        'created_at'
    ]
    
    list_filter = [
        'total_subscriptions',
        'created_at'
    ]
    
    search_fields = [
        'user__phone',
        'user__username',
        'user__first_name',
        'user__last_name'
    ]
    
    readonly_fields = [
        'current_limit',
        'current_usage',
        'tasks_remaining',
        'needs_payment',
        'get_active_bundle_info',
        'created_at',
        'updated_at'
    ]
    
    ordering = ['-created_at']
    
    def get_active_bundle_info(self, obj):
        """عرض معلومات الحزمة النشطة"""
        bundle = obj.get_active_bundle()
        if bundle:
            return f"Bundle #{bundle.id}: {bundle.tasks_used}/{bundle.tasks_included} مهام"
        return "لا توجد حزمة نشطة"
    get_active_bundle_info.short_description = "الحزمة النشطة"
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user',)
        }),
        ('المهام المجانية', {
            'fields': ('free_tasks_used',)
        }),
        ('الاشتراكات', {
            'fields': ('total_subscriptions', 'get_active_bundle_info')
        }),
        ('الحالة الحالية', {
            'fields': (
                'current_limit',
                'current_usage',
                'tasks_remaining',
                'needs_payment'
            ),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaskBundle)
class TaskBundleAdmin(admin.ModelAdmin):
    """
    إدارة حزم المهام المدفوعة
    """
    list_display = [
        'id',
        'user',
        'tasks_usage_display',
        'payment_amount',
        'moosyl_payment_status',
        'is_active',
        'purchased_at'
    ]
    
    list_filter = [
        'moosyl_payment_status',
        'is_active',
        'bundle_type',
        'purchased_at'
    ]
    
    search_fields = [
        'user__phone',
        'user__username',
        'moosyl_transaction_id'
    ]
    
    readonly_fields = [
        'is_exhausted',
        'tasks_remaining',
        'purchased_at',
        'completed_at'
    ]
    
    ordering = ['-purchased_at']
    
    def tasks_usage_display(self, obj):
        """عرض استخدام المهام بشكل مرئي"""
        percentage = (obj.tasks_used / obj.tasks_included * 100) if obj.tasks_included > 0 else 0
        color = 'green' if percentage < 50 else ('orange' if percentage < 100 else 'red')
        return f"<span style='color: {color}; font-weight: bold;'>{obj.tasks_used}/{obj.tasks_included}</span>"
    tasks_usage_display.short_description = "استخدام المهام"
    tasks_usage_display.allow_tags = True
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user',)
        }),
        ('تفاصيل الحزمة', {
            'fields': (
                'bundle_type',
                'tasks_included',
                'tasks_used',
                'tasks_remaining',
                'is_exhausted',
                'is_active'
            )
        }),
        ('معلومات الدفع - Moosyl', {
            'fields': (
                'payment_amount',
                'payment_method',
                'moosyl_transaction_id',
                'moosyl_payment_status'
            )
        }),
        ('التواريخ', {
            'fields': ('purchased_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlatformSubscription)
class PlatformSubscriptionAdmin(admin.ModelAdmin):
    """
    إدارة الاشتراكات القديمة (معطل - للتوافق فقط)
    """
    list_display = [
        'id',
        'user',
        'amount',
        'status',
        'payment_method',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'payment_method',
        'created_at'
    ]
    
    search_fields = [
        'user__phone',
        'transaction_id'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    ordering = ['-created_at']