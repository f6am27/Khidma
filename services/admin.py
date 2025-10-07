# services/admin.py
from django.contrib import admin
from .models import ServiceCategory, NouakchottArea

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name_ar', 'icon', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'name_ar']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'name_ar', 'icon')
        }),
        ('Description', {
            'fields': ('description', 'description_ar')
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )

@admin.register(NouakchottArea)
class NouakchottAreaAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name_ar', 'area_type', 'parent', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['area_type', 'is_active', 'parent']
    search_fields = ['name', 'name_ar']
    ordering = ['area_type', 'order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'name_ar', 'area_type', 'parent')
        }),
        ('Location (Optional)', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )