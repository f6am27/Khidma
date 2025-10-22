# payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model"""
    
    list_display = [
        'id',
        'task_title',
        'payer_name',
        'receiver_name',
        'amount_display',
        'payment_method',
        'status_badge',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'payment_method',
        'created_at',
        'payer__role',
        'receiver__role',
    ]
    
    search_fields = [
        'task__title',
        'payer__phone',
        'receiver__phone',
        'transaction_id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'completed_at',
    ]
    
    fieldsets = (
        ('Payment Info', {
            'fields': (
                'id',
                'task',
                'amount',
                'status',
            )
        }),
        ('Participants', {
            'fields': (
                'payer',
                'receiver',
            )
        }),
        ('Payment Method', {
            'fields': (
                'payment_method',
                'transaction_id',
            )
        }),
        ('Additional Info', {
            'fields': (
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def task_title(self, obj):
        return obj.task.title
    task_title.short_description = 'Task'
    
    def payer_name(self, obj):
        return obj.payer.get_full_name() or obj.payer.phone
    payer_name.short_description = 'Payer'
    
    def receiver_name(self, obj):
        return obj.receiver.get_full_name() or obj.receiver.phone
    receiver_name.short_description = 'Receiver'
    
    def amount_display(self, obj):
        return f"{obj.amount} MRU"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FF9800',
            'completed': '#4CAF50',
            'cancelled': '#F44336',
        }
        color = colors.get(obj.status, '#2196F3')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 5px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'