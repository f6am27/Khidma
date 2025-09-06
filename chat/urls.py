# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # المحادثات - Conversations
    path(
        'conversations/',
        views.ConversationListView.as_view(),
        name='conversation-list'
    ),
    path(
        'conversations/<int:conversation_id>/messages/',
        views.ConversationMessagesView.as_view(),
        name='conversation-messages'
    ),
    path(
        'conversations/<int:conversation_id>/send/',
        views.send_message,
        name='send-message'
    ),
    path(
        'conversations/<int:conversation_id>/',
        views.delete_conversation,
        name='delete-conversation'
    ),
    
    # إحصائيات - Statistics
    path(
        'unread-count/',
        views.unread_messages_count,
        name='unread-count'
    ),
    
    # التبليغات - Reports
    path(
        'reports/',
        views.CreateReportView.as_view(),
        name='create-report'
    ),
    path(
        'reports/my/',
        views.UserReportsView.as_view(),
        name='user-reports'
    ),
    
    # الحظر - Blocking
    path(
        'block/<int:user_id>/',
        views.block_user,
        name='block-user'
    ),
    path(
        'unblock/<int:user_id>/',
        views.unblock_user,
        name='unblock-user'
    ),
    path(
        'blocked-users/',
        views.blocked_users_list,
        name='blocked-users'
    ),
]