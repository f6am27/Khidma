# workers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import WorkerProfile, WorkerService, WorkerGallery, WorkerExperience


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'username', 'phone', 'service_area', 'total_jobs_completed', 
        'average_rating', 'is_verified', 'is_available', 'is_online'
    ]
    list_filter = [
        'is_verified', 'is_available', 'is_online', 
        'created_at', 'average_rating'
    ]
    search_fields = [
        'profile__user__username', 'profile__phone', 
        'service_area', 'bio'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_seen']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('profile', 'bio', 'service_area', 'profile_image')
        }),
        ('Availability', {
            'fields': ('available_days', 'work_start_time', 'work_end_time')
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
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_seen'),
            'classes': ('collapse',)
        })
    )
    
    def username(self, obj):
        return obj.profile.user.username
    username.short_description = 'Username'
    
    def phone(self, obj):
        return obj.profile.phone
    phone.short_description = 'Phone'


class WorkerServiceInline(admin.TabularInline):
    model = WorkerService
    extra = 1
    fields = ['category', 'base_price', 'price_type', 'is_active']


class WorkerGalleryInline(admin.TabularInline):
    model = WorkerGallery
    extra = 1
    fields = ['image', 'caption', 'service_category', 'is_featured']


@admin.register(WorkerService)
class WorkerServiceAdmin(admin.ModelAdmin):
    list_display = [
        'worker_username', 'category', 'base_price', 'price_type', 
        'is_active', 'created_at'
    ]
    list_filter = ['price_type', 'is_active', 'category', 'created_at']
    search_fields = [
        'worker__profile__user__username', 'category__name', 'description'
    ]
    ordering = ['-created_at']
    
    def worker_username(self, obj):
        return obj.worker.profile.user.username
    worker_username.short_description = 'Worker'


@admin.register(WorkerGallery)
class WorkerGalleryAdmin(admin.ModelAdmin):
    list_display = [
        'worker_username', 'caption', 'service_category', 
        'is_featured', 'image_preview', 'created_at'
    ]
    list_filter = ['is_featured', 'service_category', 'created_at']
    search_fields = ['worker__profile__user__username', 'caption']
    ordering = ['-created_at']
    
    def worker_username(self, obj):
        return obj.worker.profile.user.username
    worker_username.short_description = 'Worker'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(WorkerExperience)
class WorkerExperienceAdmin(admin.ModelAdmin):
    list_display = [
        'worker_username', 'title', 'start_date', 'end_date', 'created_at'
    ]
    list_filter = ['start_date', 'end_date', 'created_at']
    search_fields = ['worker__profile__user__username', 'title', 'description']
    ordering = ['-start_date']
    
    def worker_username(self, obj):
        return obj.worker.profile.user.username
    worker_username.short_description = 'Worker'


# Enhance the WorkerProfile admin with inlines
WorkerProfileAdmin.inlines = [WorkerServiceInline, WorkerGalleryInline]