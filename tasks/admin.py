# tasks/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'client_name', 'service_category', 'status',
        'budget', 'final_price', 'applications_count_display',
        'assigned_worker_name', 'created_at'
    ]
    list_filter = [
        'status', 'service_category', 'is_urgent', 
        'requires_materials', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'client__user__username',
        'client__user__first_name', 'client__user__last_name',
        'location'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'accepted_at',
        'work_completed_at', 'completed_at', 'cancelled_at'
    ]
    
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'service_category', 'client')
        }),
        ('Pricing & Location', {
            'fields': ('budget', 'final_price', 'location', 'latitude', 'longitude', 'preferred_time')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_worker', 'is_urgent', 'requires_materials')
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'accepted_at',
                'work_completed_at', 'completed_at', 'cancelled_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.username
    client_name.short_description = 'Client'
    
    def assigned_worker_name(self, obj):
        if obj.assigned_worker:
            return obj.assigned_worker.user.get_full_name() or obj.assigned_worker.user.username
        return '-'
    assigned_worker_name.short_description = 'Assigned Worker'
    
    def applications_count_display(self, obj):
        count = obj.applications_count
        if count > 0:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
                count
            )
        return '0'
    applications_count_display.short_description = 'Applications'
    
    actions = ['mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='work_completed').update(
            status='completed',
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} tasks marked as completed.')
    mark_as_completed.short_description = 'Mark selected tasks as completed'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status__in=['published', 'active']).update(
            status='cancelled',
            cancelled_at=timezone.now()
        )
        self.message_user(request, f'{updated} tasks cancelled.')
    mark_as_cancelled.short_description = 'Cancel selected tasks'


@admin.register(TaskApplication)
class TaskApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'worker_name', 'task_title', 'application_status', 'applied_at'
    ]
    list_filter = [
        'application_status', 'is_active', 'applied_at',
        'service_request__status', 'service_request__service_category'
    ]
    search_fields = [
        'worker__profile__user__username',
        'worker__profile__user__first_name',
        'worker__profile__user__last_name',
        'service_request__title'
    ]
    readonly_fields = ['applied_at', 'responded_at']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('service_request', 'worker', 'application_status')
        }),
        ('Message', {
            'fields': ('application_message',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'responded_at'),
            'classes': ('collapse',)
        })
    )
    
    def worker_name(self, obj):
        return obj.worker.user.get_full_name() or obj.worker.user.username
    worker_name.short_description = 'Worker'
    
    def task_title(self, obj):
        return obj.service_request.title
    task_title.short_description = 'Task'
    
    actions = ['accept_applications', 'reject_applications']
    
    def accept_applications(self, request, queryset):
        updated = queryset.filter(application_status='pending').update(
            application_status='accepted',
            responded_at=timezone.now()
        )
        self.message_user(request, f'{updated} applications accepted.')
    accept_applications.short_description = 'Accept selected applications'
    
    def reject_applications(self, request, queryset):
        updated = queryset.filter(application_status='pending').update(
            application_status='rejected',
            responded_at=timezone.now()
        )
        self.message_user(request, f'{updated} applications rejected.')
    reject_applications.short_description = 'Reject selected applications'


@admin.register(TaskReview)
class TaskReviewAdmin(admin.ModelAdmin):
    list_display = [
        'task_title', 'client_name', 'worker_name', 
        'rating', 'would_recommend', 'is_public', 'created_at'
    ]
    list_filter = [
        'rating', 'would_recommend', 'is_public', 'created_at'
    ]
    search_fields = [
        'service_request__title',
        'client__user__username', 'worker__profile__user__username',
        'review_text'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('service_request', 'client', 'worker')
        }),
        ('Rating', {
            'fields': ('rating',)
        }),
        ('Review Content', {
            'fields': ('review_text', 'would_recommend', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def task_title(self, obj):
        return obj.service_request.title
    task_title.short_description = 'Task'
    
    def client_name(self, obj):
        return obj.client.user.get_full_name() or obj.client.user.username
    client_name.short_description = 'Client'
    
    def worker_name(self, obj):
        return obj.worker.user.get_full_name() or obj.worker.user.username
    worker_name.short_description = 'Worker'


@admin.register(TaskNotification)
class TaskNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_name', 'notification_type', 'title',
        'is_read', 'is_sent', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_sent', 'created_at'
    ]
    search_fields = [
        'recipient__user__username',
        'title', 'message'
    ]
    readonly_fields = ['created_at', 'read_at', 'sent_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('service_request', 'task_application'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_sent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at', 'sent_at'),
            'classes': ('collapse',)
        })
    )
    
    def recipient_name(self, obj):
        return obj.recipient.user.get_full_name() or obj.recipient.user.username
    recipient_name.short_description = 'Recipient'
    
    actions = ['mark_as_read', 'mark_as_sent']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(is_sent=False).update(
            is_sent=True,
            sent_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as sent.')
    mark_as_sent.short_description = 'Mark selected notifications as sent'


# Customize admin site
admin.site.site_header = "Micro Emploi - Task Management"
admin.site.site_title = "Task Admin"
admin.site.index_title = "Task Management Dashboard"