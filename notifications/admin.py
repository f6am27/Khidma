# notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Notification, NotificationSettings, DeviceToken, NotificationLog


# ==================== Notification Admin ====================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    إدارة الإشعارات مع فلترة وبحث متقدم
    """
    list_display = [
        'id',
        'colored_type',
        'recipient_link',
        'title_preview',
        'read_status',
        'task_link',
        'formatted_created_at',
    ]
    
    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
        ('recipient', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'title',
        'message',
        'recipient__username',
        'recipient__phone',
        'recipient__first_name',
        'recipient__last_name',
    ]
    
    readonly_fields = [
        'id',
        'recipient_role',
        'created_at',
        'updated_at',
        'read_at',
        'notification_preview',
    ]
    
    fieldsets = (
        ('📬 Informations de Base', {
            'fields': (
                'id',
                'recipient',
                'notification_type',
                'recipient_role',
            )
        }),
        ('📝 Contenu', {
            'fields': (
                'title',
                'message',
                'notification_preview',
            )
        }),
        ('🔗 Liens', {
            'fields': (
                'related_task',
                'related_application',
            )
        }),
        ('📊 Statut', {
            'fields': (
                'is_read',
                'read_at',
            )
        }),
        ('🕒 Dates', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    # Actions personnalisées
    actions = [
        'mark_as_read',
        'mark_as_unread',
        'delete_selected_notifications',
    ]
    
    def colored_type(self, obj):
        """نوع الإشعار مع لون"""
        colors = {
            'task_published': '#28a745',
            'worker_applied': '#007bff',
            'task_completed': '#6f42c1',
            'payment_received': '#17a2b8',
            'payment_sent': '#17a2b8',
            'message_received': '#fd7e14',
            'service_reminder': '#ffc107',
            'service_cancelled': '#dc3545',
            'new_task_available': '#007bff',
            'application_accepted': '#28a745',
            'application_rejected': '#dc3545',
        }
        
        color = colors.get(obj.notification_type, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; '
            'border-radius: 5px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    colored_type.short_description = 'Type'
    
    def recipient_link(self, obj):
        """رابط للمستلم"""
        url = reverse('admin:users_user_change', args=[obj.recipient.id])
        role_icon = '👤' if obj.recipient.role == 'client' else '🔧'
        return format_html(
            '{} <a href="{}" target="_blank">{}</a>',
            role_icon,
            url,
            obj.recipient.get_full_name() or obj.recipient.phone
        )
    recipient_link.short_description = 'Destinataire'
    
    def title_preview(self, obj):
        """عنوان مختصر"""
        max_length = 50
        if len(obj.title) > max_length:
            return f"{obj.title[:max_length]}..."
        return obj.title
    title_preview.short_description = 'Titre'
    
    def read_status(self, obj):
        """حالة القراءة مع أيقونة"""
        if obj.is_read:
            return format_html(
                '<span style="color: green;">✓ Lu</span>'
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">● Non lu</span>'
            )
    read_status.short_description = 'Statut'
    
    def task_link(self, obj):
        """رابط للمهمة المرتبطة"""
        if obj.related_task:
            url = reverse('admin:tasks_servicerequest_change', args=[obj.related_task.id])
            return format_html(
                '<a href="{}" target="_blank">📋 Tâche #{}</a>',
                url,
                obj.related_task.id
            )
        return '-'
    task_link.short_description = 'Tâche'
    
    def formatted_created_at(self, obj):
        """تاريخ منسق"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    formatted_created_at.short_description = 'Date'
    
    def notification_preview(self, obj):
        """معاينة الإشعار"""
        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; '
            'border-left: 4px solid #007bff;">'
            '<strong style="font-size: 14px;">{}</strong><br><br>'
            '<p style="color: #6c757d; margin: 0;">{}</p>'
            '</div>',
            obj.title,
            obj.message
        )
    notification_preview.short_description = 'Aperçu'
    
    # Actions
    def mark_as_read(self, request, queryset):
        """تحديد كمقروء"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marquée(s) comme lue(s).')
    mark_as_read.short_description = '✓ Marquer comme lu'
    
    def mark_as_unread(self, request, queryset):
        """تحديد كغير مقروء"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notification(s) marquée(s) comme non lue(s).')
    mark_as_unread.short_description = '● Marquer comme non lu'
    
    def delete_selected_notifications(self, request, queryset):
        """حذف الإشعارات المحددة"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} notification(s) supprimée(s).')
    delete_selected_notifications.short_description = '🗑️ Supprimer'


# ==================== NotificationSettings Admin ====================
@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """
    إدارة إعدادات الإشعارات
    """
    list_display = [
        'id',
        'user_link',
        'user_role',
        'notifications_status',
        'formatted_updated_at',
    ]
    
    list_filter = [
        'notifications_enabled',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'user__username',
        'user__phone',
        'user__first_name',
        'user__last_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('👤 Utilisateur', {
            'fields': ('user',)
        }),
        ('⚙️ Paramètres', {
            'fields': ('notifications_enabled',)
        }),
        ('🕒 Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    date_hierarchy = 'updated_at'
    ordering = ['-updated_at']
    
    def user_link(self, obj):
        """رابط للمستخدم"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.phone
        )
    user_link.short_description = 'Utilisateur'
    
    def user_role(self, obj):
        """دور المستخدم"""
        if obj.user.role == 'client':
            return '👤 Client'
        elif obj.user.role == 'worker':
            return '🔧 Prestataire'
        return obj.user.role
    user_role.short_description = 'Rôle'
    
    def notifications_status(self, obj):
        """حالة الإشعارات"""
        if obj.notifications_enabled:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Activées</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Désactivées</span>'
            )
    notifications_status.short_description = 'Statut'
    
    def formatted_updated_at(self, obj):
        """آخر تحديث"""
        return obj.updated_at.strftime('%d/%m/%Y %H:%M')
    formatted_updated_at.short_description = 'Dernière mise à jour'


# ==================== DeviceToken Admin ====================
@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """
    إدارة رموز الأجهزة (FCM Tokens)
    """
    list_display = [
        'id',
        'user_link',
        'platform_icon',
        'device_name',
        'status_badge',
        'notifications_count',
        'last_used_formatted',
    ]
    
    list_filter = [
        'platform',
        'is_active',
        'notifications_enabled',
        'last_used',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'user__username',
        'user__phone',
        'device_name',
        'token',
    ]
    
    readonly_fields = [
        'token',
        'total_notifications_sent',
        'last_notification_sent',
        'last_used',
        'created_at',
        'updated_at',
        'freshness_indicator',
    ]
    
    fieldsets = (
        ('👤 Utilisateur', {
            'fields': ('user',)
        }),
        ('📱 Appareil', {
            'fields': (
                'platform',
                'device_name',
                'app_version',
                'token',
            )
        }),
        ('⚙️ Paramètres', {
            'fields': (
                'is_active',
                'notifications_enabled',
            )
        }),
        ('📊 Statistiques', {
            'fields': (
                'total_notifications_sent',
                'last_notification_sent',
                'freshness_indicator',
            )
        }),
        ('🕒 Dates', {
            'fields': (
                'last_used',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-last_used']
    list_per_page = 50
    
    actions = ['activate_devices', 'deactivate_devices', 'cleanup_old_tokens']
    
    def user_link(self, obj):
        """رابط للمستخدم"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        role_icon = '👤' if obj.user.role == 'client' else '🔧'
        return format_html(
            '{} <a href="{}" target="_blank">{}</a>',
            role_icon,
            url,
            obj.user.get_full_name() or obj.user.phone
        )
    user_link.short_description = 'Utilisateur'
    
    def platform_icon(self, obj):
        """أيقونة المنصة"""
        icons = {
            'android': '🤖 Android',
            'ios': '🍎 iOS',
            'web': '🌐 Web',
        }
        return icons.get(obj.platform, obj.platform)
    platform_icon.short_description = 'Plateforme'
    
    def status_badge(self, obj):
        """حالة الجهاز"""
        if obj.is_active and obj.notifications_enabled:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">✓ Actif</span>'
            )
        elif obj.is_active and not obj.notifications_enabled:
            return format_html(
                '<span style="background-color: #ffc107; color: black; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">⚠ Notif. désactivées</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">✗ Inactif</span>'
            )
    status_badge.short_description = 'Statut'
    
    def notifications_count(self, obj):
        """عدد الإشعارات المرسلة"""
        return f'{obj.total_notifications_sent} 📬'
    notifications_count.short_description = 'Notifications'
    
    def last_used_formatted(self, obj):
        """آخر استخدام"""
        if obj.last_used:
            return obj.last_used.strftime('%d/%m/%Y %H:%M')
        return '-'
    last_used_formatted.short_description = 'Dernier usage'
    
    def freshness_indicator(self, obj):
        """مؤشر حداثة الرمز"""
        if obj.is_fresh:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Récent (< 30 jours)</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⚠ Ancien (> 30 jours)</span>'
            )
    freshness_indicator.short_description = 'Fraîcheur'
    
    # Actions
    def activate_devices(self, request, queryset):
        """تفعيل الأجهزة"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} appareil(s) activé(s).')
    activate_devices.short_description = '✓ Activer'
    
    def deactivate_devices(self, request, queryset):
        """إلغاء تفعيل الأجهزة"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} appareil(s) désactivé(s).')
    deactivate_devices.short_description = '✗ Désactiver'
    
    def cleanup_old_tokens(self, request, queryset):
        """تنظيف الرموز القديمة"""
        count = DeviceToken.cleanup_old_tokens(days=60)
        self.message_user(request, f'{count} ancien(s) token(s) nettoyé(s).')
    cleanup_old_tokens.short_description = '🧹 Nettoyer anciens tokens'


# ==================== NotificationLog Admin ====================
@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    سجل إرسال الإشعارات عبر Firebase
    """
    list_display = [
        'id',
        'notification_link',
        'device_info',
        'status_badge',
        'retry_count',
        'sent_at_formatted',
    ]
    
    list_filter = [
        'status',
        'sent_at',
        'device_token__platform',
    ]
    
    search_fields = [
        'notification__title',
        'device_token__user__username',
        'device_token__user__phone',
        'firebase_message_id',
        'error_message',
    ]
    
    readonly_fields = [
        'notification',
        'device_token',
        'firebase_message_id',
        'sent_at',
        'delivered_at',
        'error_message',
        'retry_count',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('📬 Notification', {
            'fields': ('notification',)
        }),
        ('📱 Appareil', {
            'fields': ('device_token',)
        }),
        ('📊 Statut', {
            'fields': (
                'status',
                'firebase_message_id',
            )
        }),
        ('🕒 Dates', {
            'fields': (
                'sent_at',
                'delivered_at',
            )
        }),
        ('❌ Erreurs', {
            'fields': (
                'error_message',
                'retry_count',
            )
        }),
        ('🕒 Système', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def notification_link(self, obj):
        """رابط للإشعار"""
        url = reverse('admin:notifications_notification_change', args=[obj.notification.id])
        return format_html(
            '<a href="{}" target="_blank">#{} - {}</a>',
            url,
            obj.notification.id,
            obj.notification.title[:30]
        )
    notification_link.short_description = 'Notification'
    
    def device_info(self, obj):
        """معلومات الجهاز"""
        platform_icons = {
            'android': '🤖',
            'ios': '🍎',
            'web': '🌐',
        }
        icon = platform_icons.get(obj.device_token.platform, '📱')
        return f"{icon} {obj.device_token.device_name or 'Appareil'}"
    device_info.short_description = 'Appareil'
    
    def status_badge(self, obj):
        """حالة الإرسال"""
        colors = {
            'pending': ('#ffc107', '⏳ En attente'),
            'sent': ('#28a745', '✓ Envoyé'),
            'delivered': ('#17a2b8', '✓✓ Livré'),
            'failed': ('#dc3545', '✗ Échec'),
            'invalid_token': ('#6c757d', '⚠ Token invalide'),
        }
        
        color, label = colors.get(obj.status, ('#6c757d', obj.status))
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            label
        )
    status_badge.short_description = 'Statut'
    
    def sent_at_formatted(self, obj):
        """وقت الإرسال"""
        if obj.sent_at:
            return obj.sent_at.strftime('%d/%m/%Y %H:%M:%S')
        return '-'
    sent_at_formatted.short_description = 'Envoyé à'


# ==================== Inline للـ User Admin (اختياري) ====================
class NotificationInline(admin.TabularInline):
    """عرض الإشعارات في صفحة المستخدم"""
    model = Notification
    extra = 0
    max_num = 5
    fields = ['notification_type', 'title', 'is_read', 'created_at']
    readonly_fields = fields
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False