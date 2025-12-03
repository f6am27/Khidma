# payments/admin.py
"""
لوحة تحكم Admin لنظام عداد المهام والاشتراكات
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import UserTaskCounter, PlatformSubscription


# ================================
# 1️⃣ عداد المهام
# ================================

@admin.register(UserTaskCounter)
class UserTaskCounterAdmin(admin.ModelAdmin):
    """
    لوحة تحكم عداد المهام
    """
    list_display = [
        'user_info',
        'accepted_tasks_count',
        'tasks_remaining_display',
        'status_badge',
        'is_premium',
        'last_payment_date',
        'actions_buttons'
    ]
    
    list_filter = [
        'is_premium',
        ('last_payment_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'user__phone',
        'user__username',
        'user__first_name',
        'user__last_name'
    ]
    
    readonly_fields = [
        'user',
        'created_at',
        'updated_at',
        'counted_task_ids_display'
    ]
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user', 'is_premium')
        }),
        ('إحصائيات المهام', {
            'fields': (
                'accepted_tasks_count',
                'counted_task_ids_display',
                'last_payment_date',
                'last_reset_date'
            )
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'reset_counters',
        'activate_premium',
        'deactivate_premium'
    ]
    
    def user_info(self, obj):
        """عرض معلومات المستخدم"""
        user = obj.user
        name = user.get_full_name() or user.username
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            name,
            user.phone
        )
    user_info.short_description = 'المستخدم'
    
    def tasks_remaining_display(self, obj):
        """عرض المهام المتبقية"""
        remaining = obj.tasks_remaining_before_payment
        if obj.is_premium:
            return format_html(
                '<span style="color: gold;">♾️ لا حدود</span>'
            )
        elif remaining > 0:
            return format_html(
                '<span style="color: green;">✅ {}</span>',
                remaining
            )
        else:
            return format_html(
                '<span style="color: red;">⚠️ 0</span>'
            )
    tasks_remaining_display.short_description = 'متبقي'
    
    def status_badge(self, obj):
        """حالة العداد"""
        if obj.is_premium:
            return format_html(
                '<span style="background: gold; color: white; padding: 3px 8px; border-radius: 3px;">👑 Premium</span>'
            )
        elif obj.needs_payment:
            return format_html(
                '<span style="background: red; color: white; padding: 3px 8px; border-radius: 3px;">🔒 محظور</span>'
            )
        else:
            return format_html(
                '<span style="background: green; color: white; padding: 3px 8px; border-radius: 3px;">✅ نشط</span>'
            )
    status_badge.short_description = 'الحالة'
    
    def counted_task_ids_display(self, obj):
        """عرض IDs المهام المحسوبة"""
        if not obj.counted_task_ids:
            return format_html('<em>لا توجد مهام محسوبة</em>')
        
        ids_str = ', '.join(str(id) for id in obj.counted_task_ids[:10])
        total = len(obj.counted_task_ids)
        
        if total > 10:
            ids_str += f' ... ({total - 10} أخرى)'
        
        return format_html(
            '<code style="background: #f0f0f0; padding: 5px;">{}</code>',
            ids_str
        )
    counted_task_ids_display.short_description = 'IDs المهام المحسوبة'
    
    def actions_buttons(self, obj):
        """أزرار الإجراءات"""
        return format_html(
            '<a class="button" href="{}">إعادة تعيين</a> '
            '<a class="button" href="{}">عرض المستخدم</a>',
            reverse('admin:payments_usertaskcounter_change', args=[obj.pk]),
            reverse('admin:users_user_change', args=[obj.user.pk])
        )
    actions_buttons.short_description = 'إجراءات'
    
    # Actions
    def reset_counters(self, request, queryset):
        """إعادة تعيين العدادات المحددة"""
        count = 0
        for counter in queryset:
            counter.reset_counter()
            count += 1
        
        self.message_user(
            request,
            f'✅ تم إعادة تعيين {count} عداد بنجاح'
        )
    reset_counters.short_description = '🔄 إعادة تعيين العدادات المحددة'
    
    def activate_premium(self, request, queryset):
        """تفعيل Premium للمستخدمين المحددين"""
        count = queryset.update(
            is_premium=True,
            last_payment_date=timezone.now()
        )
        
        self.message_user(
            request,
            f'✅ تم تفعيل Premium لـ {count} مستخدم'
        )
    activate_premium.short_description = '👑 تفعيل Premium'
    
    def deactivate_premium(self, request, queryset):
        """إلغاء Premium للمستخدمين المحددين"""
        count = queryset.update(is_premium=False)
        
        self.message_user(
            request,
            f'✅ تم إلغاء Premium لـ {count} مستخدم'
        )
    deactivate_premium.short_description = '❌ إلغاء Premium'


# ================================
# 2️⃣ الاشتراكات
# ================================

@admin.register(PlatformSubscription)
class PlatformSubscriptionAdmin(admin.ModelAdmin):
    """
    لوحة تحكم الاشتراكات
    """
    list_display = [
        'id',
        'user_info',
        'amount_display',
        'payment_method',
        'status_badge',
        'validity_display',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'payment_method',
        ('created_at', admin.DateFieldListFilter),
        ('valid_until', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'user__phone',
        'user__username',
        'transaction_id'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'is_active_display',
        'days_remaining_display'
    ]
    
    fieldsets = (
        ('معلومات الاشتراك', {
            'fields': (
                'user',
                'amount',
                'payment_method',
                'status'
            )
        }),
        ('تفاصيل الدفع', {
            'fields': (
                'transaction_id',
                'valid_until',
                'is_active_display',
                'days_remaining_display'
            )
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        """عرض معلومات المستخدم"""
        user = obj.user
        name = user.get_full_name() or user.username
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            name,
            user.phone
        )
    user_info.short_description = 'المستخدم'
    
    def amount_display(self, obj):
        """عرض المبلغ"""
        return format_html(
            '<strong>{} MRU</strong>',
            obj.amount
        )
    amount_display.short_description = 'المبلغ'
    
    def status_badge(self, obj):
        """حالة الاشتراك"""
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red'
        }
        labels = {
            'pending': '⏳ قيد الانتظار',
            'completed': '✅ مكتمل',
            'failed': '❌ فشل'
        }
        
        color = colors.get(obj.status, 'gray')
        label = labels.get(obj.status, obj.status)
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            label
        )
    status_badge.short_description = 'الحالة'
    
    def validity_display(self, obj):
        """صلاحية الاشتراك"""
        if not obj.valid_until:
            return '-'
        
        now = timezone.now()
        if obj.valid_until > now:
            days = (obj.valid_until - now).days
            return format_html(
                '<span style="color: green;">✅ {} يوم</span>',
                days
            )
        else:
            return format_html(
                '<span style="color: red;">❌ منتهي</span>'
            )
    validity_display.short_description = 'الصلاحية'
    
    def is_active_display(self, obj):
        """هل نشط؟"""
        if obj.status == 'completed' and obj.valid_until and obj.valid_until > timezone.now():
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ نشط</span>'
            )
        return format_html(
            '<span style="color: red;">❌ غير نشط</span>'
        )
    is_active_display.short_description = 'نشط؟'
    
    def days_remaining_display(self, obj):
        """الأيام المتبقية"""
        if not obj.valid_until or obj.status != 'completed':
            return '-'
        
        now = timezone.now()
        if obj.valid_until > now:
            days = (obj.valid_until - now).days
            return f'{days} يوم'
        return 'منتهي'
    days_remaining_display.short_description = 'متبقي'