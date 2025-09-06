# chat/views.py
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction

from .models import Conversation, Message, BlockedUser, Report
from .serializers import (
    ConversationSerializer, MessageSerializer, SendMessageSerializer,
    ReportSerializer, CreateReportSerializer, BlockUserSerializer
)
from accounts.models import Profile


class MessagePagination(PageNumberPagination):
    """
    ترقيم الرسائل
    Message pagination
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class ConversationListView(generics.ListAPIView):
    """
    قائمة المحادثات للمستخدم
    GET /api/chat/conversations/
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        user_profile = self.request.user.profile
        
        conversations = Conversation.objects.filter(
            Q(client=user_profile) | Q(worker=user_profile),
            is_active=True
        ).select_related('client__user', 'worker__user').prefetch_related('messages')
        
        # استبعاد المحادثات مع المستخدمين المحظورين
        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user_profile) | Q(blocked=user_profile)
        ).values_list('blocker_id', 'blocked_id')
        
        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user_profile.id:
                blocked_ids.add(blocked_id)
            else:
                blocked_ids.add(blocker_id)
        
        if blocked_ids:
            conversations = conversations.exclude(
                Q(client_id__in=blocked_ids) | Q(worker_id__in=blocked_ids)
            )
        
        return conversations


class ConversationMessagesView(generics.ListAPIView):
    """
    رسائل المحادثة
    GET /api/chat/conversations/{conversation_id}/messages/
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        user_profile = self.request.user.profile
        if user_profile not in [conversation.client, conversation.worker]:
            return Message.objects.none()
        
        # تحديد الرسائل كمقروءة
        conversation.mark_messages_as_read(user_profile)
        
        return conversation.messages.select_related('sender__user').order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message(request, conversation_id):
    """
    إرسال رسالة جديدة
    POST /api/chat/conversations/{conversation_id}/send/
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user_profile = request.user.profile
    
    if user_profile not in [conversation.client, conversation.worker]:
        return Response(
            {'error': 'Vous n\'êtes pas participant à cette conversation'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not conversation.is_active:
        return Response(
            {'error': 'Cette conversation n\'est pas active'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # التحقق من عدم وجود حظر
    other_participant = conversation.worker if user_profile == conversation.client else conversation.client
    
    if BlockedUser.objects.filter(
        Q(blocker=user_profile, blocked=other_participant) |
        Q(blocker=other_participant, blocked=user_profile)
    ).exists():
        return Response(
            {'error': 'Impossible d\'envoyer un message à cet utilisateur'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = SendMessageSerializer(data=request.data)
    
    if serializer.is_valid():
        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=user_profile,
                content=serializer.validated_data['content']
            )
        
        response_serializer = MessageSerializer(message, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_conversation(request, conversation_id):
    """
    حذف المحادثة
    DELETE /api/chat/conversations/{conversation_id}/
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user_profile = request.user.profile
    
    if user_profile not in [conversation.client, conversation.worker]:
        return Response(
            {'error': 'Vous n\'êtes pas participant à cette conversation'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    conversation.is_active = False
    conversation.save()
    
    return Response({'message': 'Conversation supprimée avec succès'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_messages_count(request):
    """
    عدد الرسائل غير المقروءة الإجمالي
    GET /api/chat/unread-count/
    """
    user_profile = request.user.profile
    
    conversations = Conversation.objects.filter(
        Q(client=user_profile) | Q(worker=user_profile),
        is_active=True
    )
    
    total_unread = 0
    for conversation in conversations:
        total_unread += conversation.get_unread_count(user_profile)
    
    return Response({'unread_count': total_unread})


# نظام التبليغات
class CreateReportView(generics.CreateAPIView):
    """
    إنشاء تبليغ جديد
    POST /api/chat/reports/
    """
    serializer_class = CreateReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserReportsView(generics.ListAPIView):
    """
    تبليغات المستخدم
    GET /api/chat/reports/my/
    """
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Report.objects.filter(
            reporter=self.request.user.profile
        ).select_related('reported_user__user', 'conversation')


# نظام الحظر
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def block_user(request, user_id):
    """
    حظر مستخدم
    POST /api/chat/block/{user_id}/
    """
    data = {'blocked_user_id': user_id}
    data.update(request.data)
    
    serializer = BlockUserSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Utilisateur bloqué avec succès'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def unblock_user(request, user_id):
    """
    إلغاء حظر مستخدم
    DELETE /api/chat/unblock/{user_id}/
    """
    user_profile = request.user.profile
    
    try:
        blocked_user = BlockedUser.objects.get(
            blocker=user_profile,
            blocked_id=user_id
        )
        blocked_user.delete()
        
        return Response({'message': 'Utilisateur débloqué avec succès'})
        
    except BlockedUser.DoesNotExist:
        return Response(
            {'error': 'Cet utilisateur n\'est pas bloqué'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def blocked_users_list(request):
    """
    قائمة المستخدمين المحظورين
    GET /api/chat/blocked-users/
    """
    user_profile = request.user.profile
    
    blocked_users = BlockedUser.objects.filter(
        blocker=user_profile
    ).select_related('blocked__user')
    
    data = []
    for block in blocked_users:
        data.append({
            'id': block.blocked.id,
            'full_name': block.blocked.user.get_full_name() or block.blocked.user.username,
            'role': block.blocked.role,
            'reason': block.reason,
            'blocked_at': block.created_at
        })
    
    return Response({'blocked_users': data})