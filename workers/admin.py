
# workers/admin.py
from django.contrib import admin

# لا نسجل أي models من workers في admin panel
# كل معلومات العمال موجودة في users.WorkerProfile


# # workers/admin.py - مُصحح للنظام الجديد
# from django.contrib import admin
# from django.utils.html import format_html
# from .models import WorkerService, WorkerGallery, WorkerSettings


# class WorkerServiceInline(admin.TabularInline):
#     model = WorkerService
#     extra = 1
#     fields = ['category', 'base_price', 'price_type', 'is_active']


# class WorkerGalleryInline(admin.TabularInline):
#     model = WorkerGallery
#     extra = 1
#     fields = ['image', 'caption', 'service_category', 'is_featured']


# @admin.register(WorkerService)
# class WorkerServiceAdmin(admin.ModelAdmin):
#     list_display = [
#         'worker_name', 'category', 'base_price', 'price_type', 
#         'is_active', 'created_at'
#     ]
#     list_filter = ['price_type', 'is_active', 'category', 'created_at']
#     search_fields = [
#         'worker__first_name', 'worker__last_name', 'worker__phone', 
#         'category__name', 'description'
#     ]
#     ordering = ['-created_at']
    
#     def worker_name(self, obj):
#         return obj.worker.get_full_name() or obj.worker.phone
#     worker_name.short_description = 'Worker'


# @admin.register(WorkerGallery)
# class WorkerGalleryAdmin(admin.ModelAdmin):
#     list_display = [
#         'worker_name', 'caption', 'service_category', 
#         'is_featured', 'image_preview', 'created_at'
#     ]
#     list_filter = ['is_featured', 'service_category', 'created_at']
#     search_fields = ['worker__first_name', 'worker__last_name', 'caption']
#     ordering = ['-created_at']
    
#     def worker_name(self, obj):
#         return obj.worker.get_full_name() or obj.worker.phone
#     worker_name.short_description = 'Worker'
    
#     def image_preview(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
#                 obj.image.url
#             )
#         return '-'
#     image_preview.short_description = 'Preview'


# @admin.register(WorkerSettings)
# class WorkerSettingsAdmin(admin.ModelAdmin):
#     list_display = [
#         'worker_name', 'language', 'theme_preference', 'profile_visibility',
#         'auto_accept_jobs', 'max_daily_jobs', 'updated_at'
#     ]
#     list_filter = [
#         'language', 'theme_preference', 'profile_visibility',
#         'auto_accept_jobs', 'instant_booking'
#     ]
#     search_fields = ['worker__first_name', 'worker__last_name']
#     readonly_fields = ['created_at', 'updated_at']
    
#     fieldsets = (
#         ('Worker', {
#             'fields': ('worker',)
#         }),
#         ('Notification Settings', {
#             'fields': (
#                 'push_notifications', 'email_notifications', 'sms_notifications'
#             )
#         }),
#         ('App Preferences', {
#             'fields': ('theme_preference', 'language')
#         }),
#         ('Work Settings', {
#             'fields': (
#                 'auto_accept_jobs', 'max_daily_jobs', 'instant_booking'
#             )
#         }),
#         ('Privacy Settings', {
#             'fields': ('profile_visibility',)
#         }),
#         ('Location Settings', {
#             'fields': ('travel_radius_km',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def worker_name(self, obj):
#         return obj.worker.get_full_name() or obj.worker.phone
#     worker_name.short_description = 'Worker'