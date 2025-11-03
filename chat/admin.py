# chat/admin.py - النسخة الصحيحة المعدلة
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from .models import Conversation, Message, BlockedUser, Report


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """إدارة المحادثات"""
    list_display = [
        'id', 'client_info', 'worker_info', 'total_messages',
        'is_active', 'deleted_by_client', 'deleted_by_worker',
        'deleted_at_display', 'last_message_at', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'last_message_at']
    search_fields = [
        'client__username', 'client__first_name', 'client__last_name',
        'worker__username', 'worker__first_name', 'worker__last_name'
    ]
    readonly_fields = ['total_messages', 'created_at', 'updated_at', 'last_message_at']
    ordering = ['-last_message_at', '-created_at']
    
    fieldsets = (
        ('Participants', {
            'fields': ('client', 'worker')
        }),
        ('État', {
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
        if obj.client:
            name = obj.client.get_full_name() or obj.client.username
            return format_html(
                '<strong>{}</strong><br><small>@{}</small>',
                name, obj.client.username
            )
        return '-'
    client_info.short_description = 'Client'
    
    def worker_info(self, obj):
        if obj.worker:
            name = obj.worker.get_full_name() or obj.worker.username
            return format_html(
                '<strong>{}</strong><br><small>@{}</small>',
                name, obj.worker.username
            )
        return '-'
    worker_info.short_description = 'Worker'

    def deleted_at_display(self, obj):
        """عرض تاريخ الحذف"""
        result = []
        if obj.deleted_at_by_client:
            result.append(format_html(
                '👤 <span style="color: orange;">Client: {}</span>',
                obj.deleted_at_by_client.strftime('%Y-%m-%d %H:%M')
            ))
        if obj.deleted_at_by_worker:
            result.append(format_html(
                '🔧 <span style="color: blue;">Worker: {}</span>',
                obj.deleted_at_by_worker.strftime('%Y-%m-%d %H:%M')
            ))
        return format_html('<br>'.join(result)) if result else '-'
    deleted_at_display.short_description = 'تاريخ الحذف'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'worker'
        ).annotate(
            message_count=Count('messages')
        )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """إدارة الرسائل"""
    list_display = [
        'id', 'conversation_info', 'sender_info', 'content_preview',
        'is_read', 'created_at'
    ]
    list_filter = ['is_read', 'created_at', 'conversation__is_active']
    search_fields = [
        'content', 'sender__username',
        'conversation__client__username',
        'conversation__worker__username'
    ]
    readonly_fields = ['conversation', 'sender', 'created_at', 'updated_at', 'read_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Message', {
            'fields': ('conversation', 'sender', 'content')
        }),
        ('État', {
            'fields': ('is_read', 'read_at')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def conversation_info(self, obj):
        client_name = obj.conversation.client.get_full_name() or obj.conversation.client.username
        worker_name = obj.conversation.worker.get_full_name() or obj.conversation.worker.username
        return format_html(
            '<small>#{}</small><br>{} ↔ {}',
            obj.conversation.id, client_name[:15], worker_name[:15]
        )
    conversation_info.short_description = 'Conversation'
    
    def sender_info(self, obj):
        name = obj.sender.get_full_name() or obj.sender.username
        role_badge = "👤" if obj.sender.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.sender.username
        )
    sender_info.short_description = 'Expéditeur'
    
    def content_preview(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = 'Contenu'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'conversation__client',
            'conversation__worker',
            'sender'
        )


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    """إدارة المستخدمين المحظورين"""
    list_display = [
        'id', 'blocker_info', 'blocked_info', 'reason', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'blocker__username', 'blocker__first_name',
        'blocked__username', 'blocked__first_name',
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
        name = obj.blocker.get_full_name() or obj.blocker.username
        role_badge = "👤" if obj.blocker.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.blocker.username
        )
    blocker_info.short_description = 'Bloqueur'
    
    def blocked_info(self, obj):
        name = obj.blocked.get_full_name() or obj.blocked.username
        role_badge = "👤" if obj.blocked.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.blocked.username
        )
    blocked_info.short_description = 'Bloqué'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'blocker', 'blocked'
        )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """إدارة التبليغات"""
    list_display = [
        'id', 
        'reporter_info', 
        'reported_user_info_with_count',
        'reason',
        'status', 
        'created_at', 
        'resolved_at'
    ]
    
    list_filter = [
        'status',
        'reason',
        'created_at',
        'resolved_at',
        ('reporter', admin.RelatedOnlyFieldListFilter),
        ('reported_user', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'id',
        'reporter__username', 
        'reported_user__username',
        'description', 
        'admin_notes'
    ]
    
    readonly_fields = ['reporter', 'reported_user', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    actions = [
        'mark_as_resolved',
        'mark_as_dismissed',
        'suspend_user_3days',
        'suspend_user_7days',
        'suspend_user_30days',
        'permanent_ban',
    ]
    
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
        name = obj.reporter.get_full_name() or obj.reporter.username
        role_badge = "👤" if obj.reporter.role == 'client' else "🔧"
        return format_html(
            '{} <strong>{}</strong><br><small>@{}</small>',
            role_badge, name, obj.reporter.username
        )
    reporter_info.short_description = 'Rapporteur'
    
    def reported_user_info_with_count(self, obj):
        """معلومات المُبلَّغ عنه مع عداد البلاغات"""
        name = obj.reported_user.get_full_name() or obj.reported_user.username
        role_badge = "👤" if obj.reported_user.role == 'client' else "🔧"
        
        total_reports = Report.objects.filter(
            reported_user=obj.reported_user
        ).count()
        
        resolved_reports = Report.objects.filter(
            reported_user=obj.reported_user,
            status='resolved'
        ).count()
        
        if total_reports >= 3:
            color = 'red'
            icon = '🚨'
        elif total_reports >= 2:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'green'
            icon = '✓'
        
        return format_html(
            '{} <strong>{}</strong><br>'
            '<small>@{}</small><br>'
            '<span style="color: {}; font-weight: bold;">'
            '{} البلاغات: {} (محلول: {})'
            '</span>',
            role_badge, name, obj.reported_user.username,
            color, icon, total_reports, resolved_reports
        )
    reported_user_info_with_count.short_description = 'Utilisateur signalé'
    
    # ============= ACTIONS =============
    
    def mark_as_resolved(self, request, queryset):
        """✅ تم حل المشكلة"""
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='resolved',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'✅ تم تحديد {updated} بلاغ كمحلول')
    mark_as_resolved.short_description = "✅ تم حل المشكلة"
    
    def mark_as_dismissed(self, request, queryset):
        """❌ رفض البلاغ"""
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='dismissed',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'❌ تم رفض {updated} بلاغ')
    mark_as_dismissed.short_description = "❌ رفض البلاغ"
    
    def suspend_user_3days(self, request, queryset):
        """⏸️ تعليق 3 أيام"""
        count = 0
        for report in queryset:
            user = report.reported_user
            
            user.is_suspended = True
            # user.is_active = False
            user.suspended_until = timezone.now() + timedelta(days=3)
            user.suspension_reason = f"تعليق 3 أيام - بلاغ #{report.id}"
            user.save(update_fields=['is_suspended', 'is_active', 'suspended_until', 'suspension_reason'])
            
            report.status = 'resolved'
            report.resolved_at = timezone.now()
            report.resolved_by = request.user
            report.admin_notes = f"تعليق 3 أيام حتى {user.suspended_until.strftime('%Y-%m-%d %H:%M')}"
            report.save(update_fields=['status', 'resolved_at', 'resolved_by', 'admin_notes'])
            
            count += 1
        
        self.message_user(request, f"✅ تم تعليق {count} مستخدم لمدة 3 أيام")
    suspend_user_3days.short_description = "⏸️ تعليق 3 أيام"
    
    def suspend_user_7days(self, request, queryset):
        """⏸️ تعليق 7 أيام"""
        count = 0
        for report in queryset:
            user = report.reported_user
            
            user.is_suspended = True
            # user.is_active = False
            user.suspended_until = timezone.now() + timedelta(days=7)
            user.suspension_reason = f"تعليق 7 أيام - بلاغ #{report.id}"
            user.save(update_fields=['is_suspended', 'is_active', 'suspended_until', 'suspension_reason'])
            
            report.status = 'resolved'
            report.resolved_at = timezone.now()
            report.resolved_by = request.user
            report.admin_notes = f"تعليق 7 أيام حتى {user.suspended_until.strftime('%Y-%m-%d %H:%M')}"
            report.save(update_fields=['status', 'resolved_at', 'resolved_by', 'admin_notes'])
            
            count += 1
        
        self.message_user(request, f"✅ تم تعليق {count} مستخدم لمدة 7 أيام")
    suspend_user_7days.short_description = "⏸️ تعليق 7 أيام"
    
    def suspend_user_30days(self, request, queryset):
        """⏸️ تعليق 30 يوم"""
        count = 0
        for report in queryset:
            user = report.reported_user
            
            user.is_suspended = True
            # user.is_active = False
            user.suspended_until = timezone.now() + timedelta(days=30)
            user.suspension_reason = f"تعليق 30 يوم - بلاغ #{report.id}"
            user.save(update_fields=['is_suspended', 'is_active', 'suspended_until', 'suspension_reason'])
            
            report.status = 'resolved'
            report.resolved_at = timezone.now()
            report.resolved_by = request.user
            report.admin_notes = f"تعليق 30 يوم حتى {user.suspended_until.strftime('%Y-%m-%d %H:%M')}"
            report.save(update_fields=['status', 'resolved_at', 'resolved_by', 'admin_notes'])
            
            count += 1
        
        self.message_user(request, f"✅ تم تعليق {count} مستخدم لمدة 30 يوم")
    suspend_user_30days.short_description = "⏸️ تعليق 30 يوم"
    
    def permanent_ban(self, request, queryset):
        """🚫 حظر نهائي"""
        count = 0
        for report in queryset:
            user = report.reported_user
            
            user.is_suspended = True
            user.is_active = False
            user.suspended_until = None
            user.suspension_reason = f"حظر نهائي - بلاغ #{report.id}"
            user.save(update_fields=['is_suspended', 'is_active', 'suspended_until', 'suspension_reason'])
            
            report.status = 'resolved'
            report.resolved_at = timezone.now()
            report.resolved_by = request.user
            report.admin_notes = "تم حظر الحساب نهائياً"
            report.save(update_fields=['status', 'resolved_at', 'resolved_by', 'admin_notes'])
            
            count += 1
        
        self.message_user(request, f'🚫 تم حظر {count} مستخدم نهائياً', level='WARNING')
    permanent_ban.short_description = "🚫 حظر نهائي"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'reporter', 'reported_user', 'resolved_by'
        )