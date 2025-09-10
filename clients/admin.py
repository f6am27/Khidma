# clients/admin.py - مُصحح للنظام الجديد
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FavoriteWorker, ClientSettings


@admin.register(FavoriteWorker)
class FavoriteWorkerAdmin(admin.ModelAdmin):
    list_display = [
        'client_link', 'worker_link', 'worker_name', 'worker_rating',
        'times_hired', 'total_spent_with_worker', 'added_at'
    ]
    list_filter = ['added_at', 'times_hired']
    search_fields = [
        'client__first_name', 'client__last_name', 'client__phone',
        'worker__first_name', 'worker__last_name', 'notes'
    ]
    readonly_fields = ['added_at', 'last_contacted']
    
    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:users_user_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.get_full_name())
        return '-'
    client_link.short_description = 'Client'
    
    def worker_link(self, obj):
        if obj.worker:
            url = reverse('admin:users_user_change', args=[obj.worker.id])
            return format_html('<a href="{}">{}</a>', url, obj.worker.get_full_name())
        return '-'
    worker_link.short_description = 'Worker'
    
    def worker_name(self, obj):
        return obj.worker.get_full_name() if obj.worker else '-'
    worker_name.short_description = 'Worker Name'
    
    def worker_rating(self, obj):
        if obj.worker and hasattr(obj.worker, 'worker_profile'):
            rating = obj.worker.worker_profile.average_rating
            stars = '★' * int(rating) + '☆' * (5 - int(rating))
            return format_html(
                '<span title="{:.1f}/5">{}</span>',
                rating, stars
            )
        return '-'
    worker_rating.short_description = 'Rating'


@admin.register(ClientSettings)
class ClientSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'client_link', 'language', 'theme_preference', 'profile_visibility',
        'push_notifications', 'email_notifications', 'updated_at'
    ]
    list_filter = [
        'language', 'theme_preference', 'profile_visibility',
        'push_notifications', 'email_notifications'
    ]
    search_fields = ['client__first_name', 'client__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Client', {
            'fields': ('client',)
        }),
        ('Notification Settings', {
            'fields': (
                'push_notifications', 'email_notifications', 'sms_notifications'
            )
        }),
        ('App Preferences', {
            'fields': ('theme_preference', 'language')
        }),
        ('Privacy Settings', {
            'fields': (
                'profile_visibility', 'allow_contact_from_workers'
            )
        }),
        ('Location Settings', {
            'fields': ('auto_detect_location', 'search_radius_km')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:users_user_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.get_full_name())
        return '-'
    client_link.short_description = 'Client'


# Custom admin site modifications
admin.site.site_header = "Micro Emploi Administration"
admin.site.site_title = "Micro Emploi Admin"
admin.site.index_title = "Welcome to Micro Emploi Administration"