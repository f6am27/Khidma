# tasks/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg, Sum, Q
from django.urls import reverse
from django.utils import timezone
from .models import ServiceRequest, TaskApplication, TaskReview, TaskNotification


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    """
    إدارة طلبات الخدمة (المهام)
    """
    list_display = [
        'id',
        'title_display',
        'client_display',
        'category_display',
        'budget_display',
        'status_display',
        'worker_display',
        'applications_count',
        'urgency_display',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'is_urgent',
        'requires_materials',
        'service_category',
        'created_at',
        ('assigned_worker', admin.EmptyFieldListFilter),
        ('final_price', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'title',
        'description',
        'location',
        'client__phone',
        'client__first_name',
        'client__last_name',
        'assigned_worker__phone',
        'assigned_worker__first_name',
        'assigned_worker__last_name'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'accepted_at',
        # 'work_started_at',
        # 'work_completed_at',
        # 'completed_at',
        'cancelled_at',
        'timeline_display',
        'location_display',
        'statistics_display'
    ]
    
    fieldsets = (
        ('Task Information', {
            'fields': (
                'title',
                'description',
                'service_category',
                'client'
            )
        }),
        ('Pricing', {
            'fields': ('budget', 'final_price')
        }),
        ('Location & Timing', {
            'fields': (
                'location',
                'latitude',
                'longitude',
                'location_display',
                'preferred_time',
                'time_description'
            )
        }),
        ('Worker Assignment', {
            'fields': ('assigned_worker',)
        }),
        ('Status & Options', {
            'fields': (
                'status',
                'is_urgent',
                'requires_materials'
            )
        }),
        ('Timeline', {
            'fields': (
                'created_at',
                'accepted_at',
                # 'work_started_at',
                # 'work_completed_at',
                # 'completed_at',
                'cancelled_at',
                'updated_at',
                'timeline_display'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('statistics_display',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 30
    
    def title_display(self, obj):
        status_colors = {
            'published': '#2196F3',
            'active': '#FF9800',
            'work_completed': '#9C27B0',
            'completed': '#4CAF50',
            'cancelled': '#F44336'
        }
        
        color = status_colors.get(obj.status, '#666')
        prefix = 'URGENT: ' if obj.is_urgent else ''
        
        return format_html(
            '<strong style="color:{};">{}{}</strong>',
            color,
            prefix,
            obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
        )
    title_display.short_description = 'Title'
    
    def client_display(self, obj):
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
            client.phone[:8] + '...',
            total_tasks
        )
    client_display.short_description = 'Client'
    
    def category_display(self, obj):
        return format_html(
            '<span style="background:#E3F2FD; color:#1976D2; padding:4px 10px; '
            'border-radius:12px; font-size:11px;">{}</span>',
            obj.service_category.name
        )
    category_display.short_description = 'Category'
    
    def budget_display(self, obj):
        if obj.final_price:
            return format_html(
                '<strong style="color:#4CAF50;">{} MRU</strong><br>'
                '<small style="color:#999;">Budget: {} MRU</small>',
                f'{float(obj.final_price):,.0f}',
                obj.budget
            )
        return format_html(
            '<strong style="color:#666;">{} MRU</strong>',
            obj.budget
        )
    budget_display.short_description = 'Budget'
    
    def status_display(self, obj):
        status_config = {
            'published': {'color': '#2196F3', 'bg': '#E3F2FD'},
            'active': {'color': '#FF9800', 'bg': '#FFF3E0'},
            'work_completed': {'color': '#9C27B0', 'bg': '#F3E5F5'},
            'completed': {'color': '#4CAF50', 'bg': '#E8F5E9'},
            'cancelled': {'color': '#F44336', 'bg': '#FFEBEE'}
        }
        
        config = status_config.get(obj.status, {'color': '#666', 'bg': '#f5f5f5'})
        
        return format_html(
            '<span style="background:{}; color:{}; padding:6px 12px; '
            'border-radius:16px; font-weight:bold; display:inline-block;">{}</span>',
            config['bg'],
            config['color'],
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def worker_display(self, obj):
        if not obj.assigned_worker:
            return format_html('<span style="color:#999;">Not assigned</span>')
        
        worker = obj.assigned_worker
        url = reverse('admin:users_user_change', args=[worker.id])
        
        rating = 0.0
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            rating = worker.worker_profile.average_rating
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#388E3C;">{}</strong><br>'
            '<small style="color:#666;">Rating: {}/5</small>'
            '</a>',
            url,
            worker.get_full_name() or worker.phone,
            rating
        )
    worker_display.short_description = 'Worker'
    
    def applications_count(self, obj):
        count = obj.applications.filter(is_active=True).count()
        
        if count == 0:
            color = '#9E9E9E'
            bg = '#f5f5f5'
        elif count < 3:
            color = '#2196F3'
            bg = '#E3F2FD'
        elif count < 5:
            color = '#FF9800'
            bg = '#FFF3E0'
        else:
            color = '#4CAF50'
            bg = '#E8F5E9'
        
        return format_html(
            '<a href="/admin/tasks/taskapplication/?service_request__id__exact={}" '
            'style="background:{}; color:{}; padding:6px 12px; border-radius:12px; '
            'text-decoration:none; font-weight:bold;">{} applicants</a>',
            obj.id,
            bg,
            color,
            count
        )
    applications_count.short_description = 'Applications'
    
    def urgency_display(self, obj):
        if obj.is_urgent:
            return format_html(
                '<span style="background:#FF5252; color:white; padding:4px 10px; '
                'border-radius:12px; font-weight:bold;">URGENT</span>'
            )
        return format_html('<span style="color:#999;">Normal</span>')
    urgency_display.short_description = 'Priority'
    
    def timeline_display(self, obj):
        timeline = []
        
        timeline.append({
            'event': 'Task Published',
            'date': obj.created_at,
            'color': '#2196F3'
        })
        
        if obj.accepted_at:
            timeline.append({
                'event': 'Worker Accepted',
                'date': obj.accepted_at,
                'color': '#4CAF50'
            })
        
        # if obj.work_started_at:
        #     timeline.append({
        #         'event': 'Work Started',
        #         'date': obj.work_started_at,
        #         'color': '#FF9800'
        #     })
        
        # if obj.work_completed_at:
        #     timeline.append({
        #         'event': 'Work Completed',
        #         'date': obj.work_completed_at,
        #         'color': '#9C27B0'
        #     })
        
        # if obj.completed_at:
        #     timeline.append({
        #         'event': 'Task Completed',
        #         'date': obj.completed_at,
        #         'color': '#4CAF50'
        #     })
        
        if obj.cancelled_at:
            timeline.append({
                'event': 'Task Cancelled',
                'date': obj.cancelled_at,
                'color': '#F44336'
            })
        
        html = '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Timeline</h3>'
        
        for item in timeline:
            html += f'<div style="margin:10px 0; padding:10px; background:white; border-left:4px solid {item["color"]}; border-radius:4px;">'
            html += f'<strong style="color:{item["color"]};">{item["event"]}</strong><br>'
            html += f'<small style="color:#666;">{item["date"].strftime("%Y-%m-%d %H:%M")}</small>'
            html += '</div>'
        
        if obj.completed_at:
            duration = obj.completed_at - obj.created_at
            days = duration.days
            hours = duration.seconds // 3600
            html += f'<p style="margin-top:15px;"><strong>Total Duration:</strong> {days} days, {hours} hours</p>'
        
        html += '</div>'
        
        return format_html(html)
    timeline_display.short_description = 'Timeline'
    
    def location_display(self, obj):
        if obj.latitude and obj.longitude:
            maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            
            return format_html(
                '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
                '<h3 style="margin-top:0; color:#1976D2;">Location on Map</h3>'
                '<p><strong>Address:</strong> {}</p>'
                '<p><strong>Latitude:</strong> {}</p>'
                '<p><strong>Longitude:</strong> {}</p>'
                '<iframe width="100%" height="300" frameborder="0" style="border:0; border-radius:8px;" '
                'src="https://maps.google.com/maps?q={},{}&output=embed"></iframe>'
                '<p style="margin-top:10px;">'
                '<a href="{}" target="_blank" class="button">Open in Google Maps</a>'
                '</p>'
                '</div>',
                obj.location,
                obj.latitude,
                obj.longitude,
                obj.latitude,
                obj.longitude,
                maps_url
            )
        else:
            return format_html(
                '<div style="background:#FFF3E0; padding:15px; border-radius:8px; border-left:4px solid #FF9800;">'
                '<p style="margin:0;"><strong>Location:</strong> {}</p>'
                '<small style="color:#666;">No GPS coordinates available</small>'
                '</div>',
                obj.location
            )
    location_display.short_description = 'Location Map'
    
    def statistics_display(self, obj):
        total_applications = obj.applications.count()
        pending_applications = obj.applications.filter(application_status='pending').count()
        accepted_applications = obj.applications.filter(application_status='accepted').count()
        rejected_applications = obj.applications.filter(application_status='rejected').count()
        
        review_info = 'Not reviewed yet'
        if hasattr(obj, 'review'):
            review = obj.review
            review_info = f'{review.rating}/5 stars'
        
        html = '<div style="background:#E3F2FD; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Task Statistics</h3>'
        html += f'<p><strong>Total Applications:</strong> {total_applications}</p>'
        html += f'<p><strong>Pending:</strong> {pending_applications}</p>'
        html += f'<p><strong>Accepted:</strong> {accepted_applications}</p>'
        html += f'<p><strong>Rejected:</strong> {rejected_applications}</p>'
        
        if obj.final_price:
            savings = float(obj.budget) - float(obj.final_price)
            html += f'<p><strong>Final Price:</strong> {float(obj.final_price):,.0f} MRU</p>'
            html += f'<p><strong>Original Budget:</strong> {obj.budget} MRU</p>'
            if savings > 0:
                html += f'<p style="color:#4CAF50;"><strong>Saved:</strong> {savings:,.0f} MRU</p>'
            elif savings < 0:
                html += f'<p style="color:#F44336;"><strong>Over Budget:</strong> {abs(savings):,.0f} MRU</p>'
        
        html += f'<p><strong>Review:</strong> {review_info}</p>'
        html += f'<p><strong>Urgent:</strong> {"Yes" if obj.is_urgent else "No"}</p>'
        html += f'<p><strong>Requires Materials:</strong> {"Yes" if obj.requires_materials else "No"}</p>'
        html += '</div>'
        
        return format_html(html)
    statistics_display.short_description = 'Statistics'
    
    actions = ['mark_as_urgent', 'mark_as_not_urgent', 'cancel_tasks']
    
    def mark_as_urgent(self, request, queryset):
        count = queryset.update(is_urgent=True)
        self.message_user(request, f'Marked {count} tasks as urgent')
    mark_as_urgent.short_description = 'Mark as urgent'
    
    def mark_as_not_urgent(self, request, queryset):
        count = queryset.update(is_urgent=False)
        self.message_user(request, f'Removed urgent status from {count} tasks')
    mark_as_not_urgent.short_description = 'Remove urgent status'
    
    def cancel_tasks(self, request, queryset):
        valid_statuses = ['published', 'active']
        tasks_to_cancel = queryset.filter(status__in=valid_statuses)
        count = tasks_to_cancel.update(
            status='cancelled',
            cancelled_at=timezone.now()
        )
        self.message_user(request, f'Cancelled {count} tasks')
    cancel_tasks.short_description = 'Cancel tasks'


@admin.register(TaskApplication)
class TaskApplicationAdmin(admin.ModelAdmin):
    """
    إدارة تقدمات العمال للمهام
    """
    list_display = [
        'id',
        'task_display',
        'worker_display',
        'status_display',
        'applied_at',
        'message_preview'
    ]
    
    list_filter = [
        'application_status',
        'is_active',
        'applied_at',
        'service_request__status',
        'service_request__service_category'
    ]
    
    search_fields = [
        'worker__phone',
        'worker__first_name',
        'worker__last_name',
        'service_request__title',
        'application_message'
    ]
    
    readonly_fields = [
        'applied_at',
        'responded_at',
        'application_details',
        'worker_profile',
        'task_details'
    ]
    
    fieldsets = (
        ('Application Info', {
            'fields': (
                'service_request',
                'worker',
                'application_message',
                'application_status',
                'is_active'
            )
        }),
        ('Dates', {
            'fields': ('applied_at', 'responded_at'),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': (
                'application_details',
                'worker_profile',
                'task_details'
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'applied_at'
    ordering = ['-applied_at']
    list_per_page = 30
    
    def task_display(self, obj):
        task = obj.service_request
        url = reverse('admin:tasks_servicerequest_change', args=[task.id])
        
        status_colors = {
            'published': '#2196F3',
            'active': '#FF9800',
            'completed': '#4CAF50',
            'cancelled': '#F44336'
        }
        
        color = status_colors.get(task.status, '#666')
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:{};">{}</strong><br>'
            '<small style="color:#666;">{} MRU | {}</small>'
            '</a>',
            url,
            color,
            task.title[:40] + '...' if len(task.title) > 40 else task.title,
            task.budget,
            task.get_status_display()
        )
    task_display.short_description = 'Task'
    
    def worker_display(self, obj):
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
            worker.phone[:8] + '...',
            rating
        )
    worker_display.short_description = 'Worker'
    
    def status_display(self, obj):
        status_config = {
            'pending': {'color': '#FF9800', 'bg': '#FFF3E0'},
            'accepted': {'color': '#4CAF50', 'bg': '#E8F5E9'},
            'rejected': {'color': '#F44336', 'bg': '#FFEBEE'}
        }
        
        config = status_config.get(obj.application_status, {'color': '#666', 'bg': '#f5f5f5'})
        
        return format_html(
            '<span style="background:{}; color:{}; padding:6px 12px; '
            'border-radius:16px; font-weight:bold; display:inline-block;">{}</span>',
            config['bg'],
            config['color'],
            obj.get_application_status_display()
        )
    status_display.short_description = 'Status'
    
    def message_preview(self, obj):
        message = obj.application_message or ''
        if len(message) > 50:
            return format_html(
                '<span style="color:#666;" title="{}">{}</span>',
                message,
                message[:50] + '...'
            )
        return format_html('<span style="color:#666;">{}</span>', message or '—')
    message_preview.short_description = 'Message'
    
    def application_details(self, obj):
        html = '<div style="background:#f5f5f5; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Application Details</h3>'
        html += f'<p><strong>Status:</strong> {obj.get_application_status_display()}</p>'
        html += f'<p><strong>Active:</strong> {"Yes" if obj.is_active else "No"}</p>'
        html += f'<p><strong>Applied:</strong> {obj.applied_at.strftime("%Y-%m-%d %H:%M")}</p>'
        
        if obj.responded_at:
            html += f'<p><strong>Responded:</strong> {obj.responded_at.strftime("%Y-%m-%d %H:%M")}</p>'
            duration = obj.responded_at - obj.applied_at
            hours = duration.total_seconds() / 3600
            html += f'<p><strong>Response Time:</strong> {hours:.1f} hours</p>'
        
        html += f'<div style="margin-top:15px; padding:10px; background:white; border-radius:4px;">'
        html += f'<strong>Message:</strong><br>'
        html += f'<p style="color:#666; margin-top:5px;">{obj.application_message or "No message"}</p>'
        html += '</div>'
        html += '</div>'
        
        return format_html(html)
    application_details.short_description = 'Application Details'
    
    def worker_profile(self, obj):
        worker = obj.worker
        
        rating = 0.0
        total_jobs = 0
        total_reviews = 0
        
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            profile = worker.worker_profile
            rating = profile.average_rating
            total_jobs = profile.total_jobs_completed
            total_reviews = profile.total_reviews
        
        html = '<div style="background:#E8F5E9; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#388E3C;">Worker Profile</h3>'
        html += f'<p><strong>Name:</strong> {worker.get_full_name() or "N/A"}</p>'
        html += f'<p><strong>Phone:</strong> {worker.phone}</p>'
        html += f'<p><strong>Rating:</strong> {rating}/5</p>'
        html += f'<p><strong>Reviews:</strong> {total_reviews}</p>'
        html += f'<p><strong>Completed Jobs:</strong> {total_jobs}</p>'
        html += f'<p><strong>Verified:</strong> {"Yes" if worker.is_verified else "No"}</p>'
        html += '</div>'
        
        return format_html(html)
    worker_profile.short_description = 'Worker Profile'
    
    def task_details(self, obj):
        task = obj.service_request
        
        html = '<div style="background:#E3F2FD; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Task Details</h3>'
        html += f'<p><strong>Title:</strong> {task.title}</p>'
        html += f'<p><strong>Category:</strong> {task.service_category.name}</p>'
        html += f'<p><strong>Budget:</strong> {task.budget} MRU</p>'
        html += f'<p><strong>Location:</strong> {task.location}</p>'
        html += f'<p><strong>Status:</strong> {task.get_status_display()}</p>'
        html += f'<p><strong>Preferred Time:</strong> {task.preferred_time}</p>'
        html += f'<p><strong>Urgent:</strong> {"Yes" if task.is_urgent else "No"}</p>'
        
        total_apps = task.applications.count()
        html += f'<p><strong>Total Applicants:</strong> {total_apps}</p>'
        
        html += '</div>'
        
        return format_html(html)
    task_details.short_description = 'Task Details'
    
    actions = ['accept_applications', 'reject_applications', 'mark_as_inactive']
    
    def accept_applications(self, request, queryset):
        pending_apps = queryset.filter(application_status='pending')
        count = pending_apps.update(
            application_status='accepted',
            responded_at=timezone.now()
        )
        self.message_user(request, f'Accepted {count} applications')
    accept_applications.short_description = 'Accept applications'
    
    def reject_applications(self, request, queryset):
        pending_apps = queryset.filter(application_status='pending')
        count = pending_apps.update(
            application_status='rejected',
            responded_at=timezone.now()
        )
        self.message_user(request, f'Rejected {count} applications')
    reject_applications.short_description = 'Reject applications'
    
    def mark_as_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Marked {count} applications as inactive')
    mark_as_inactive.short_description = 'Mark as inactive'


@admin.register(TaskReview)
class TaskReviewAdmin(admin.ModelAdmin):
    """
    إدارة تقييمات المهام
    """
    list_display = [
        'id',
        'task_title',
        'client_display',
        'worker_display',
        'rating_display',
        'review_preview',
        'recommend_display',
        'public_display',
        'created_at'
    ]
    
    list_filter = [
        'rating',
        'would_recommend',
        'is_public',
        'created_at',
        'service_request__service_category'
    ]
    
    search_fields = [
        'service_request__title',
        'client__phone',
        'client__first_name',
        'worker__phone',
        'worker__first_name',
        'review_text'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'review_details',
        'task_summary',
        'client_summary',
        'worker_summary'
    ]
    
    fieldsets = (
        ('Review', {
            'fields': (
                'service_request',
                'client',
                'worker',
                'rating',
                'review_text',
                'would_recommend',
                'is_public'
            )
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': (
                'review_details',
                'task_summary',
                'client_summary',
                'worker_summary'
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 30
    
    def task_title(self, obj):
        task = obj.service_request
        url = reverse('admin:tasks_servicerequest_change', args=[task.id])
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#1976D2;">{}</strong>'
            '</a>',
            url,
            task.title[:40] + '...' if len(task.title) > 40 else task.title
        )
    task_title.short_description = 'Task'
    
    def client_display(self, obj):
        client = obj.client
        url = reverse('admin:users_user_change', args=[client.id])
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#1976D2;">{}</strong><br>'
            '<small style="color:#666;">{}</small>'
            '</a>',
            url,
            client.get_full_name() or client.phone,
            client.phone[:8] + '...'
        )
    client_display.short_description = 'Client'
    
    def worker_display(self, obj):
        worker = obj.worker
        url = reverse('admin:users_user_change', args=[worker.id])
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:#388E3C;">{}</strong><br>'
            '<small style="color:#666;">{}</small>'
            '</a>',
            url,
            worker.get_full_name() or worker.phone,
            worker.phone[:8] + '...'
        )
    worker_display.short_description = 'Worker'
    
    def rating_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        color = '#4CAF50' if obj.rating >= 4 else '#FF9800' if obj.rating >= 3 else '#F44336'
        
        return format_html(
            '<span style="font-size:18px; color:{};">{}</span><br>'
            '<small style="color:#666;">{}/5</small>',
            color,
            stars,
            obj.rating
        )
    rating_display.short_description = 'Rating'
    
    def review_preview(self, obj):
        text = obj.review_text or ''
        if len(text) > 60:
            return format_html(
                '<span style="color:#666;" title="{}">{}</span>',
                text,
                text[:60] + '...'
            )
        return format_html('<span style="color:#666;">{}</span>', text or '—')
    review_preview.short_description = 'Comment'
    
    def recommend_display(self, obj):
        if obj.would_recommend:
            return format_html(
                '<span style="background:#E8F5E9; color:#4CAF50; padding:4px 10px; '
                'border-radius:12px; font-weight:bold;">Recommends</span>'
            )
        return format_html(
            '<span style="background:#FFEBEE; color:#F44336; padding:4px 10px; '
            'border-radius:12px; font-weight:bold;">Not Recommend</span>'
        )
    recommend_display.short_description = 'Recommendation'
    
    def public_display(self, obj):
        if obj.is_public:
            return format_html('<span style="color:#4CAF50;">Public</span>')
        return format_html('<span style="color:#9E9E9E;">Private</span>')
    public_display.short_description = 'Visibility'
    
    def review_details(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        
        html = '<div style="background:#FFF3E0; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#F57C00;">Review Details</h3>'
        html += f'<p><strong>Stars:</strong> <span style="font-size:20px; color:#FF9800;">{stars}</span> ({obj.rating}/5)</p>'
        html += f'<p><strong>Recommends:</strong> {"Yes" if obj.would_recommend else "No"}</p>'
        html += f'<p><strong>Public:</strong> {"Yes" if obj.is_public else "No (Private)"}</p>'
        html += f'<p><strong>Created:</strong> {obj.created_at.strftime("%Y-%m-%d %H:%M")}</p>'
        
        if obj.updated_at != obj.created_at:
            html += f'<p><strong>Updated:</strong> {obj.updated_at.strftime("%Y-%m-%d %H:%M")}</p>'
        
        html += '<div style="margin-top:15px; padding:10px; background:white; border-radius:4px;">'
        html += '<strong>Review Text:</strong><br>'
        html += f'<p style="color:#666; margin-top:5px;">{obj.review_text or "No comment"}</p>'
        html += '</div>'
        html += '</div>'
        
        return format_html(html)
    review_details.short_description = 'Review Details'
    
    def task_summary(self, obj):
        task = obj.service_request
        
        html = '<div style="background:#E3F2FD; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Task Summary</h3>'
        html += f'<p><strong>Title:</strong> {task.title}</p>'
        html += f'<p><strong>Category:</strong> {task.service_category.name}</p>'
        html += f'<p><strong>Budget:</strong> {task.budget} MRU</p>'
        
        if task.final_price:
            html += f'<p><strong>Final Price:</strong> {float(task.final_price):,.0f} MRU</p>'
        
        html += f'<p><strong>Location:</strong> {task.location}</p>'
        html += f'<p><strong>Created:</strong> {task.created_at.strftime("%Y-%m-%d")}</p>'
        
        if task.completed_at:
            html += f'<p><strong>Completed:</strong> {task.completed_at.strftime("%Y-%m-%d")}</p>'
        
        html += '</div>'
        
        return format_html(html)
    task_summary.short_description = 'Task Summary'
    
    def client_summary(self, obj):
        client = obj.client
        from tasks.models import ServiceRequest, TaskReview
        
        total_tasks = ServiceRequest.objects.filter(client=client).count()
        completed_tasks = ServiceRequest.objects.filter(client=client, status='completed').count()
        total_reviews_given = TaskReview.objects.filter(client=client).count()
        
        html = '<div style="background:#E8F5E9; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#388E3C;">Client Summary</h3>'
        html += f'<p><strong>Name:</strong> {client.get_full_name() or "N/A"}</p>'
        html += f'<p><strong>Phone:</strong> {client.phone}</p>'
        html += f'<p><strong>Total Tasks:</strong> {total_tasks}</p>'
        html += f'<p><strong>Completed:</strong> {completed_tasks}</p>'
        html += f'<p><strong>Reviews Given:</strong> {total_reviews_given}</p>'
        html += '</div>'
        
        return format_html(html)
    client_summary.short_description = 'Client Summary'
    
    def worker_summary(self, obj):
        worker = obj.worker
        
        rating = 0.0
        total_jobs = 0
        total_reviews = 0
        
        if hasattr(worker, 'worker_profile') and worker.worker_profile:
            profile = worker.worker_profile
            rating = profile.average_rating
            total_jobs = profile.total_jobs_completed
            total_reviews = profile.total_reviews
        
        html = '<div style="background:#FFF3E0; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#F57C00;">Worker Summary</h3>'
        html += f'<p><strong>Name:</strong> {worker.get_full_name() or "N/A"}</p>'
        html += f'<p><strong>Phone:</strong> {worker.phone}</p>'
        html += f'<p><strong>Current Rating:</strong> {rating}/5</p>'
        html += f'<p><strong>Total Reviews:</strong> {total_reviews}</p>'
        html += f'<p><strong>Completed Jobs:</strong> {total_jobs}</p>'
        html += '</div>'
        
        return format_html(html)
    worker_summary.short_description = 'Worker Summary'
    
    actions = ['make_public', 'make_private']
    
    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, f'Made {count} reviews public')
    make_public.short_description = 'Make public'
    
    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, f'Made {count} reviews private')
    make_private.short_description = 'Make private'


@admin.register(TaskNotification)
class TaskNotificationAdmin(admin.ModelAdmin):
    """
    إدارة إشعارات المهام
    """
    list_display = [
        'id',
        'recipient_display',
        'notification_type_display',
        'title_preview',
        'read_status',
        'sent_status',
        'created_at'
    ]
    
    list_filter = [
        'notification_type',
        'is_read',
        'is_sent',
        'created_at',
        'read_at',
        'sent_at'
    ]
    
    search_fields = [
        'recipient__phone',
        'recipient__first_name',
        'recipient__last_name',
        'title',
        'message',
        'service_request__title'
    ]
    
    readonly_fields = [
        'created_at',
        'read_at',
        'sent_at',
        'notification_details'
    ]
    
    fieldsets = (
        ('Recipient', {
            'fields': ('recipient',)
        }),
        ('Notification Content', {
            'fields': (
                'notification_type',
                'title',
                'message'
            )
        }),
        ('Links', {
            'fields': (
                'service_request',
                'task_application'
            )
        }),
        ('Status', {
            'fields': (
                'is_read',
                'is_sent'
            )
        }),
        ('Dates', {
            'fields': (
                'created_at',
                'read_at',
                'sent_at'
            ),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('notification_details',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 30
    
    def recipient_display(self, obj):
        recipient = obj.recipient
        url = reverse('admin:users_user_change', args=[recipient.id])
        
        role_color = '#1976D2' if recipient.role == 'client' else '#388E3C'
        
        return format_html(
            '<a href="{}" style="text-decoration:none;">'
            '<strong style="color:{};">{}</strong><br>'
            '<small style="color:#666;">{}</small>'
            '</a>',
            url,
            role_color,
            recipient.get_full_name() or recipient.phone,
            recipient.phone[:8] + '...'
        )
    recipient_display.short_description = 'Recipient'
    
    def notification_type_display(self, obj):
        type_colors = {
            'task_posted': '#2196F3',
            'application_received': '#FF9800',
            'application_accepted': '#4CAF50',
            'application_rejected': '#F44336',
            'work_started': '#9C27B0',
            'work_completed': '#00BCD4',
            'task_completed': '#4CAF50',
            'payment_completed': '#8BC34A',
            'review_received': '#FFC107',
            'task_cancelled': '#F44336'
        }
        
        color = type_colors.get(obj.notification_type, '#666')
        
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    notification_type_display.short_description = 'Type'
    
    def title_preview(self, obj):
        return format_html(
            '<strong style="color:#333;">{}</strong>',
            obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
        )
    title_preview.short_description = 'Title'
    
    def read_status(self, obj):
        if obj.is_read:
            time_str = obj.read_at.strftime('%Y-%m-%d %H:%M') if obj.read_at else ''
            return format_html(
                '<span style="color:#4CAF50;">Read</span><br>'
                '<small style="color:#666;">{}</small>',
                time_str
            )
        return format_html(
            '<span style="color:#FF9800; font-weight:bold;">Unread</span>'
        )
    read_status.short_description = 'Read'
    
    def sent_status(self, obj):
        if obj.is_sent:
            time_str = obj.sent_at.strftime('%Y-%m-%d %H:%M') if obj.sent_at else ''
            return format_html(
                '<span style="color:#4CAF50;">Sent</span><br>'
                '<small style="color:#666;">{}</small>',
                time_str
            )
        return format_html(
            '<span style="color:#F44336;">Not Sent</span>'
        )
    sent_status.short_description = 'Sent'
    
    def notification_details(self, obj):
        html = '<div style="background:#E3F2FD; padding:15px; border-radius:8px;">'
        html += '<h3 style="margin-top:0; color:#1976D2;">Notification Details</h3>'
        html += f'<p><strong>Type:</strong> {obj.get_notification_type_display()}</p>'
        html += f'<p><strong>Title:</strong> {obj.title}</p>'
        html += f'<p><strong>Created:</strong> {obj.created_at.strftime("%Y-%m-%d %H:%M")}</p>'
        html += f'<p><strong>Read:</strong> {"Yes" if obj.is_read else "No"}</p>'
        
        if obj.is_read and obj.read_at:
            html += f'<p><strong>Read At:</strong> {obj.read_at.strftime("%Y-%m-%d %H:%M")}</p>'
            time_to_read = obj.read_at - obj.created_at
            minutes = time_to_read.total_seconds() / 60
            html += f'<p><strong>Time to Read:</strong> {minutes:.0f} minutes</p>'
        
        html += f'<p><strong>Sent:</strong> {"Yes" if obj.is_sent else "No"}</p>'
        
        if obj.is_sent and obj.sent_at:
            html += f'<p><strong>Sent At:</strong> {obj.sent_at.strftime("%Y-%m-%d %H:%M")}</p>'
        
        html += '<div style="margin-top:15px; padding:10px; background:white; border-radius:4px;">'
        html += '<strong>Message:</strong><br>'
        html += f'<p style="color:#666; margin-top:5px;">{obj.message}</p>'
        html += '</div>'
        
        recipient = obj.recipient
        html += '<div style="margin-top:15px; padding:10px; background:#f5f5f5; border-radius:4px;">'
        html += '<strong>Recipient:</strong><br>'
        html += f'<p style="margin-top:5px;"><strong>Name:</strong> {recipient.get_full_name() or "N/A"}</p>'
        html += f'<p><strong>Phone:</strong> {recipient.phone}</p>'
        html += f'<p><strong>Role:</strong> {recipient.role.title()}</p>'
        html += '</div>'
        
        if obj.service_request:
            task = obj.service_request
            html += '<div style="margin-top:15px; padding:10px; background:#FFF3E0; border-radius:4px;">'
            html += '<strong>Related Task:</strong><br>'
            html += f'<p style="margin-top:5px;"><strong>Title:</strong> {task.title}</p>'
            html += f'<p><strong>Status:</strong> {task.get_status_display()}</p>'
            html += f'<p><strong>Budget:</strong> {task.budget} MRU</p>'
            html += '</div>'
        
        html += '</div>'
        
        return format_html(html)
    notification_details.short_description = 'Notification Details'
    
    actions = ['mark_as_read', 'mark_as_unread', 'mark_as_sent', 'delete_notifications']
    
    def mark_as_read(self, request, queryset):
        count = queryset.update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'Marked {count} notifications as read')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        count = queryset.update(
            is_read=False,
            read_at=None
        )
        self.message_user(request, f'Marked {count} notifications as unread')
    mark_as_unread.short_description = 'Mark as unread'
    
    def mark_as_sent(self, request, queryset):
        count = queryset.update(
            is_sent=True,
            sent_at=timezone.now()
        )
        self.message_user(request, f'Marked {count} notifications as sent')
    mark_as_sent.short_description = 'Mark as sent'
    
    def delete_notifications(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Deleted {count} notifications')
    delete_notifications.short_description = 'Delete notifications'