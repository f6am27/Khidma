# clients/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ClientProfile, FavoriteWorker, ClientSettings


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'profile_link', 'full_name', 'phone_display', 'is_verified', 
        'total_tasks_published', 'total_tasks_completed', 'success_rate_display',
        'total_amount_spent', 'last_activity', 'is_active'
    ]
    list_filter = [
        'is_verified', 'is_active', 'gender', 'preferred_language',
        'notifications_enabled', 'created_at'
    ]
    search_fields = [
        'profile__user__username', 'profile__user__first_name', 
        'profile__user__last_name', 'profile__phone', 'bio'
    ]
    readonly_fields = [
        'profile', 'total_tasks_published', 'total_tasks_completed',
        'total_amount_spent', 'created_at', 
        'updated_at', 'last_activity'
    ]
    
    fieldsets = (
        ('Profile Information', {
            'fields': ('profile', 'bio', 'profile_image')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'gender', 'address', 'emergency_contact')
        }),
        ('Statistics', {
            'fields': (
                'total_tasks_published', 'total_tasks_completed', 
                'total_amount_spent'
            ),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': (
                'preferred_language', 'notifications_enabled', 
                'email_notifications', 'sms_notifications'
            )
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active', 'last_activity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def profile_link(self, obj):
        if obj.profile:
            url = reverse('admin:accounts_profile_change', args=[obj.profile.id])
            return format_html('<a href="{}">{}</a>', url, obj.profile.user.username)
        return '-'
    profile_link.short_description = 'Profile'
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def phone_display(self, obj):
        return obj.profile.phone if obj.profile else '-'
    phone_display.short_description = 'Phone'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    actions = ['verify_clients', 'deactivate_clients', 'activate_clients']
    
    def verify_clients(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} clients have been verified.')
    verify_clients.short_description = 'Verify selected clients'
    
    def deactivate_clients(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} clients have been deactivated.')
    deactivate_clients.short_description = 'Deactivate selected clients'
    
    def activate_clients(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} clients have been activated.')
    activate_clients.short_description = 'Activate selected clients'


@admin.register(FavoriteWorker)
class FavoriteWorkerAdmin(admin.ModelAdmin):
    list_display = [
        'client_link', 'worker_link', 'worker_name', 'worker_rating',
        'times_hired', 'total_spent_with_worker', 'added_at'
    ]
    list_filter = ['added_at', 'times_hired']
    search_fields = [
        'client__user__username', 'worker__profile__user__first_name',
        'worker__profile__user__last_name', 'notes'
    ]
    readonly_fields = ['added_at', 'last_contacted']
    
    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:accounts_profile_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.user.username)
        return '-'
    client_link.short_description = 'Client'
    
    def worker_link(self, obj):
        if obj.worker:
            url = reverse('admin:workers_workerprofile_change', args=[obj.worker.id])
            return format_html('<a href="{}">{}</a>', url, obj.worker_full_name)
        return '-'
    worker_link.short_description = 'Worker'
    
    def worker_name(self, obj):
        return obj.worker_full_name
    worker_name.short_description = 'Worker Name'
    
    def worker_rating(self, obj):
        rating = obj.worker.average_rating
        stars = '★' * int(rating) + '☆' * (5 - int(rating))
        return format_html(
            '<span title="{:.1f}/5">{}</span>',
            rating, stars
        )
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
    search_fields = ['client__user__username']
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
                'profile_visibility', 'show_last_seen', 
                'allow_contact_from_workers'
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
            url = reverse('admin:accounts_profile_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.user.username)
        return '-'
    client_link.short_description = 'Client'


# Custom admin site modifications
admin.site.site_header = "Micro Emploi Administration"
admin.site.site_title = "Micro Emploi Admin"
admin.site.index_title = "Welcome to Micro Emploi Administration"