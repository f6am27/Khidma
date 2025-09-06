# chat/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from .models import Conversation, Message, BlockedUser, Report


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    إدارة المحادثات
    Conversation admin
    """
    list_display = [
        'id', 'client_info', 'worker_info', 'total_messages',
        'is_active', 'last_message_at', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'last_message_at']
    search_fields = [
        'client__user__username', 'client__user__first_name', 'client__user__last_name',
        'worker__user__username', 'worker__user__first_name', 'worker__user__last_name'
    ]
    readonly_fields = ['total_messages', 'created_at', 'updated_at', 'last_message_at']
    ordering = ['-last_message_at', '-created_at']
    
    fieldsets = (
        ('Participants', {
            'fields': ('client', 'worker')
        }),
        ('État de la conversation', {
            'fields': ('is_active',)
        }),
        ('Statistiques', {
            'fields': ('total_messages', 'last_message_at'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def client_info(self, obj):
        """معلومات العميل"""
        if obj.client:
            name = obj.client.user.get_full_name() or obj.client.user.username
            return format_html(
                '<strong>{}</strong><br><small>@{}</small>',
                name, obj.client.user.username
            )
        return '-'
    client_info.short_description = 'Client'
    
    def worker_info(self, obj):
        """معلومات العامل"""
        if obj.worker:
            name = obj.worker.user.get_full_name() or obj.worker.user.username
            return format_html(
                '<strong>{}</strong><br><small>@{}</small>',
                name, obj.worker.user.username
            )
        return '-'
    worker_info.short_description = 'Worker'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client__user', 'worker__user'
        ).annotate(
            message_count=Count('messages')
        )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    إدارة الرسائل
    Message admin
    """
    list_display = [
        'id', 'conversation_info', 'sender_info', 'content_preview',
        'is_read', 'created_at'
    ]
    list_filter = ['is_read', 'created_at', 'conversation__is_active']
    search_fields = [
        'content', 'sender__user__username',
        'conversation__client__user__username',
        'conversation__worker__user__username'
    ]
    readonly_fields = ['conversation', 'sender', 'created_at', 'updated_at', 'read_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Message', {
            'fields': ('conversation', 'sender', 'content')
        }),
        ('État de lecture', {
            'fields': ('is_read', 'read_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def conversation_info(self, obj):
        """معلومات المحادثة"""
        client_name = obj.conversation.client.user.get_full_name() or obj.conversation.client.user.username
        worker_name = obj.conversation.worker.user.get_full_name() or obj.conversation.worker.user.username
        return format_html(
            '<small>#{}</small><br>{} ↔ {}',
            obj.conversation.id, client_name[:15], worker_name[:15]
        )
    conversation_info.short_description = 'Conversation'
    
    def sender_info(self, obj):
        """معلومات المرسل"""
        name = obj.sender.user.get_full_name() or obj.sender.user.username
        role_badge = "👤" if obj.sender.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.sender.user.username
        )
    sender_info.short_description = 'Expéditeur'
    
    def content_preview(self, obj):
        """معاينة المحتوى"""
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = 'Contenu'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'conversation__client__user',
            'conversation__worker__user',
            'sender__user'
        )


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    """
    إدارة المستخدمين المحظورين
    Blocked users admin
    """
    list_display = [
        'id', 'blocker_info', 'blocked_info', 'reason', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'blocker__user__username', 'blocker__user__first_name',
        'blocked__user__username', 'blocked__user__first_name',
        'reason'
    ]
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Blocage', {
            'fields': ('blocker', 'blocked', 'reason')
        }),
        ('Date', {
            'fields': ('created_at',)
        }),
    )
    
    def blocker_info(self, obj):
        """معلومات المستخدم الحاظر"""
        name = obj.blocker.user.get_full_name() or obj.blocker.user.username
        role_badge = "👤" if obj.blocker.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.blocker.user.username
        )
    blocker_info.short_description = 'Bloqueur'
    
    def blocked_info(self, obj):
        """معلومات المستخدم المحظور"""
        name = obj.blocked.user.get_full_name() or obj.blocked.user.username
        role_badge = "👤" if obj.blocked.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.blocked.user.username
        )
    blocked_info.short_description = 'Bloqué'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'blocker__user', 'blocked__user'
        )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    إدارة التبليغات
    Reports admin
    """
    list_display = [
        'id', 'reporter_info', 'reported_user_info', 'reason',
        'status', 'created_at', 'resolved_at'
    ]
    list_filter = [
        'status', 'reason', 'created_at', 'resolved_at'
    ]
    search_fields = [
        'reporter__user__username', 'reported_user__user__username',
        'description', 'admin_notes'
    ]
    readonly_fields = ['reporter', 'reported_user', 'created_at', 'updated_at']
    ordering = ['-created_at']
    actions = ['mark_as_resolved', 'mark_as_dismissed']
    
    fieldsets = (
        ('Signalement', {
            'fields': ('reporter', 'reported_user', 'conversation')
        }),
        ('Détails', {
            'fields': ('reason', 'description')
        }),
        ('Traitement', {
            'fields': ('status', 'admin_notes', 'resolved_by', 'resolved_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def reporter_info(self, obj):
        """معلومات المبلِّغ"""
        name = obj.reporter.user.get_full_name() or obj.reporter.user.username
        role_badge = "👤" if obj.reporter.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.reporter.user.username
        )
    reporter_info.short_description = 'Rapporteur'
    
    def reported_user_info(self, obj):
        """معلومات المُبلَّغ عنه"""
        name = obj.reported_user.user.get_full_name() or obj.reported_user.user.username
        role_badge = "👤" if obj.reported_user.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.reported_user.user.username
        )
    reported_user_info.short_description = 'Utilisateur signalé'
    
    def mark_as_resolved(self, request, queryset):
        """تحديد التبليغات كمُحلولة"""
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='resolved',
            resolved_at=timezone.now(),
            resolved_by=request.user.profile if hasattr(request.user, 'profile') else None
        )
        
        self.message_user(
            request,
            f'{updated} signalement(s) marqué(s) comme résolu(s).'
        )
    mark_as_resolved.short_description = "Marquer comme résolu"
    
    def mark_as_dismissed(self, request, queryset):
        """رفض التبليغات"""
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='dismissed',
            resolved_at=timezone.now(),
            resolved_by=request.user.profile if hasattr(request.user, 'profile') else None
        )
        
        self.message_user(
            request,
            f'{updated} signalement(s) rejeté(s).'
        )
    mark_as_dismissed.short_description = "Rejeter"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'reporter__user', 'reported_user__user', 'resolved_by__user'
        )