# clients/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Q
from django.urls import reverse
from django.utils import timezone
from .models import FavoriteWorker, ClientSettings


@admin.register(FavoriteWorker)
class FavoriteWorkerAdmin(admin.ModelAdmin):
    """
    إدارة العمال المفضلين للعملاء
    """
    list_display = [
        'id',
        'client_name',
        'worker_name', 
        'added_at',
        'last_contacted'
    ]
    
    list_filter = [
        'added_at',
        'last_contacted',
    ]
    
    search_fields = [
        'client__phone',
        'client__first_name',
        'client__last_name',
        'worker__phone',
        'worker__first_name', 
        'worker__last_name',
        'notes'
    ]
    
    readonly_fields = [
        'added_at',
        'client_details',
        'worker_details',
        'interaction_summary'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'worker', 'notes')
        }),
        ('Detailed Information', {
            'fields': ('client_details', 'worker_details', 'interaction_summary'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'added_at'
    ordering = ['-added_at']
    list_per_page = 25
    
    def client_name(self, obj):
        client = obj.client
        url = reverse('admin:users_user_change', args=[client.id])
        
        from tasks.models import ServiceRequest
        total_tasks = ServiceRequest.objects.filter(client=client).count()
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#1976D2;">{}</strong><br>'
            '<small style="color:#666;">{} | {} tasks</small>'
            '</a>',
            url,
            client.get_full_name() or client.phone,
            client.phone,
            total_tasks
        )
    client_name.short_description = 'Client'
    
    def worker_name(self, obj):
        worker = obj.worker
        url = reverse('admin:users_user_change', args=[worker.id])
        
        rating = 0.0
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            rating = worker.worker_profile.average_rating
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#388E3C;">{}</strong><br>'
            '<small style="color:#666;">{} | Rating: {}/5</small>'
            '</a>',
            url,
            worker.get_full_name() or worker.phone,
            worker.phone,
            rating
        )
    worker_name.short_description = 'Worker'
    
    def times_hired_display(self, obj):
        if obj.times_hired == 0:
            color = '#9E9E9E'
        elif obj.times_hired < 3:
            color = '#2196F3'
        elif obj.times_hired < 5:
            color = '#FF9800'
        else:
            color = '#4CAF50'
        
        return format_html(
            '<span style="background-color:{}; color:white; padding:4px 10px; '
            'border-radius:12px; font-weight:bold;">{} times</span>',
            color,
            obj.times_hired
        )
    times_hired_display.short_description = 'Times Hired'
    
    def total_spent_display(self, obj):
        amount = float(obj.total_spent_with_worker)
        
        if amount == 0:
            color = '#9E9E9E'
        elif amount < 1000:
            color = '#2196F3'
        elif amount < 5000:
            color = '#FF9800'
        else:
            color = '#4CAF50'
        
        return format_html(
            '<span style="background-color:{}; color:white; padding:4px 10px; '
            'border-radius:12px; font-weight:bold;">{} MRU</span>',
            color,
            f'{amount:,.2f}'
        )
    total_spent_display.short_description = 'Total Spent'
    
    def client_details(self, obj):
        client = obj.client
        from tasks.models import ServiceRequest
        
        total_tasks = ServiceRequest.objects.filter(client=client).count()
        completed_tasks = ServiceRequest.objects.filter(
            client=client, 
            status='completed'
        ).count()
        
        return format_html(
            '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
            '<h3 style="margin-top:0; color:#1976D2;">Client Details</h3>'
            '<p><strong>Name:</strong> {}</p>'
            '<p><strong>Phone:</strong> {}</p>'
            '<p><strong>Email:</strong> {}</p>'
            '<p><strong>Total Tasks:</strong> {}</p>'
            '<p><strong>Completed Tasks:</strong> {}</p>'
            '<p><strong>Member Since:</strong> {}</p>'
            '<p><strong>Verified:</strong> {}</p>'
            '</div>',
            client.get_full_name() or 'N/A',
            client.phone,
            client.email or 'N/A',
            total_tasks,
            completed_tasks,
            client.date_joined.strftime('%Y-%m-%d'),
            'Yes' if client.is_verified else 'No'
        )
    client_details.short_description = 'Client Details'
    
    def worker_details(self, obj):
        worker = obj.worker
        
        rating = 0.0
        total_jobs = 0
        total_reviews = 0
        
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            profile = worker.worker_profile
            rating = profile.average_rating
            total_jobs = profile.total_jobs_completed
            total_reviews = profile.total_reviews
        
        return format_html(
            '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
            '<h3 style="margin-top:0; color:#388E3C;">Worker Details</h3>'
            '<p><strong>Name:</strong> {}</p>'
            '<p><strong>Phone:</strong> {}</p>'
            '<p><strong>Rating:</strong> {}/5 ({} reviews)</p>'
            '<p><strong>Completed Jobs:</strong> {}</p>'
            '<p><strong>Member Since:</strong> {}</p>'
            '<p><strong>Verified:</strong> {}</p>'
            '</div>',
            worker.get_full_name() or 'N/A',
            worker.phone,
            rating,
            total_reviews,
            total_jobs,
            worker.date_joined.strftime('%Y-%m-%d'),
            'Yes' if worker.is_verified else 'No'
        )
    worker_details.short_description = 'Worker Details'
    
    def interaction_summary(self, obj):
        from tasks.models import ServiceRequest
        
        tasks = ServiceRequest.objects.filter(
            client=obj.client,
            assigned_worker=obj.worker
        )
        
        completed = tasks.filter(status='completed').count()
        active = tasks.filter(status='active').count()
        total = tasks.count()
        
        return format_html(
            '<div style="background:#E3F2FD; padding:15px; border-radius:8px;">'
            '<h3 style="margin-top:0; color:#1976D2;">Interaction Summary</h3>'
            '<p><strong>Times Hired:</strong> {} times</p>'
            '<p><strong>Total Spent:</strong> {} MRU</p>'
            '<p><strong>Completed Tasks:</strong> {} out of {}</p>'
            '<p><strong>Active Tasks:</strong> {}</p>'
            '<p><strong>Last Contact:</strong> {}</p>'
            '<p><strong>Added:</strong> {}</p>'
            '</div>',
            obj.times_hired,
            f'{float(obj.total_spent_with_worker):,.2f}',
            completed,
            total,
            active,
            obj.last_contacted.strftime('%Y-%m-%d %H:%M') if obj.last_contacted else 'Never',
            obj.added_at.strftime('%Y-%m-%d %H:%M')
        )
    interaction_summary.short_description = 'Interaction Summary'
    
    
    def clear_notes(self, request, queryset):
        count = queryset.update(notes='')
        self.message_user(request, f'Cleared notes for {count} records')
    clear_notes.short_description = 'Clear notes'

@admin.register(ClientSettings)
class ClientSettingsAdmin(admin.ModelAdmin):
    """
    إدارة إعدادات العملاء
    """
    list_display = [
        'id',
        'client_name',
        'notifications_display',
        'app_preferences_display',
        'privacy_display',
        'location_display',
        'updated_at'
    ]
    
    list_filter = [
        'push_notifications',
        'email_notifications',
        'sms_notifications',
        'theme_preference',
        'language',
        'profile_visibility',
        'allow_contact_from_workers',
        'auto_detect_location',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'client__phone',
        'client__first_name',
        'client__last_name',
        'client__email'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'client_profile_summary']
    
    fieldsets = (
        ('Client', {
            'fields': ('client', 'client_profile_summary')
        }),
        ('Notification Settings', {
            'fields': (
                'push_notifications',
                'email_notifications', 
                'sms_notifications'
            )
        }),
        ('App Preferences', {
            'fields': ('theme_preference', 'language')
        }),
        ('Privacy Settings', {
            'fields': ('profile_visibility', 'allow_contact_from_workers')
        }),
        ('Location Settings', {
            'fields': ('auto_detect_location', 'search_radius_km')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'updated_at'
    ordering = ['-updated_at']
    list_per_page = 25
    
    def client_name(self, obj):
        client = obj.client
        url = reverse('admin:users_user_change', args=[client.id])
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#1976D2;">{}</strong><br>'
            '<small style="color:#666;">{}</small>'
            '</a>',
            url,
            client.get_full_name() or client.phone,
            client.phone
        )
    client_name.short_description = 'Client'
    
    def notifications_display(self, obj):
        notifications = []
        
        if obj.push_notifications:
            notifications.append('<span style="color:#4CAF50;">Push</span>')
        if obj.email_notifications:
            notifications.append('<span style="color:#2196F3;">Email</span>')
        if obj.sms_notifications:
            notifications.append('<span style="color:#FF9800;">SMS</span>')
        
        if not notifications:
            return format_html('<span style="color:#9E9E9E;">Disabled</span>')
        
        return format_html(' | '.join(notifications))
    notifications_display.short_description = 'Notifications'
    
    def app_preferences_display(self, obj):
        return format_html(
            '<span style="color:#666;">{} | {}</span>',
            obj.get_theme_preference_display(),
            obj.get_language_display()
        )
    app_preferences_display.short_description = 'Preferences'
    
    def privacy_display(self, obj):
        visibility_colors = {
            'public': '#4CAF50',
            'workers_only': '#FF9800',
            'private': '#F44336'
        }
        
        color = visibility_colors.get(obj.profile_visibility, '#9E9E9E')
        contact_status = 'Yes' if obj.allow_contact_from_workers else 'No'
        
        return format_html(
            '<span style="color:{};">{}</span><br>'
            '<small style="color:#666;">Contact: {}</small>',
            color,
            obj.get_profile_visibility_display(),
            contact_status
        )
    privacy_display.short_description = 'Privacy'
    
    def location_display(self, obj):
        auto_detect = 'Yes' if obj.auto_detect_location else 'No'
        
        return format_html(
            '<span style="color:#666;">Auto: {}</span><br>'
            '<small style="color:#666;">Radius: {} km</small>',
            auto_detect,
            obj.search_radius_km
        )
    location_display.short_description = 'Location'
    
    def client_profile_summary(self, obj):
        client = obj.client
        from tasks.models import ServiceRequest
        
        total_tasks = ServiceRequest.objects.filter(client=client).count()
        completed_tasks = ServiceRequest.objects.filter(
            client=client,
            status='completed'
        ).count()
        
        return format_html(
            '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
            '<h3 style="margin-top:0; color:#1976D2;">Activity Summary</h3>'
            '<p><strong>Name:</strong> {}</p>'
            '<p><strong>Phone:</strong> {}</p>'
            '<p><strong>Email:</strong> {}</p>'
            '<p><strong>Total Tasks:</strong> {}</p>'
            '<p><strong>Completed Tasks:</strong> {}</p>'
            '<p><strong>Verified:</strong> {}</p>'
            '<p><strong>Member Since:</strong> {}</p>'
            '</div>',
            client.get_full_name() or 'N/A',
            client.phone,
            client.email or 'N/A',
            total_tasks,
            completed_tasks,
            'Yes' if client.is_verified else 'No',
            client.date_joined.strftime('%Y-%m-%d')
        )
    client_profile_summary.short_description = 'Profile Summary'
    
    actions = ['enable_all_notifications', 'disable_all_notifications', 'reset_to_default']
    
    def enable_all_notifications(self, request, queryset):
        count = queryset.update(
            push_notifications=True,
            email_notifications=True,
            sms_notifications=True
        )
        self.message_user(request, f'Enabled notifications for {count} clients')
    enable_all_notifications.short_description = 'Enable all notifications'
    
    def disable_all_notifications(self, request, queryset):
        count = queryset.update(
            push_notifications=False,
            email_notifications=False,
            sms_notifications=False
        )
        self.message_user(request, f'Disabled notifications for {count} clients')
    disable_all_notifications.short_description = 'Disable all notifications'
    
    def reset_to_default(self, request, queryset):
        count = queryset.update(
            push_notifications=True,
            email_notifications=True,
            sms_notifications=False,
            theme_preference='auto',
            language='fr',
            profile_visibility='workers_only',
            allow_contact_from_workers=True,
            auto_detect_location=True,
            search_radius_km=10
        )
        self.message_user(request, f'Reset settings to default for {count} clients')
    reset_to_default.short_description = 'Reset to default'