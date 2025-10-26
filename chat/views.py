# chat/views.py
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from .models import Conversation, Message, BlockedUser, Report
from .serializers import (
    ConversationSerializer, MessageSerializer, SendMessageSerializer,
    ReportSerializer, CreateReportSerializer, BlockUserSerializer
)
from users.models import User


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
        user = self.request.user
        
        # ✅ استبعاد المحادثات المحذوفة من قبل المستخدم
        conversations = Conversation.objects.filter(
            Q(client=user, deleted_by_client=False) | 
            Q(worker=user, deleted_by_worker=False),
            is_active=True
        ).select_related('client', 'worker').prefetch_related('messages')
        
        # استبعاد المحادثات مع المستخدمين المحظورين
        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')
        
        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            if blocker_id == user.id:
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
        
        user = self.request.user
        if user not in [conversation.client, conversation.worker]:
            return Message.objects.none()
        
        # تحديد الرسائل كمقروءة
        conversation.mark_messages_as_read(user)
        
        # ✅ فلترة الرسائل بناءً على تاريخ الحذف (مع التحقق من None)
        messages = conversation.messages.select_related('sender').order_by('-created_at')
        
        # إذا كان المستخدم حذف المحادثة، أظهر فقط الرسائل بعد تاريخ الحذف
        if user == conversation.client and conversation.deleted_at_by_client is not None:
            messages = messages.filter(created_at__gt=conversation.deleted_at_by_client)
        elif user == conversation.worker and conversation.deleted_at_by_worker is not None:
            messages = messages.filter(created_at__gt=conversation.deleted_at_by_worker)
        
        return messages


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message(request, conversation_id):
    """
    إرسال رسالة جديدة
    POST /api/chat/conversations/{conversation_id}/send/
    """
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user
    
    if user not in [conversation.client, conversation.worker]:
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
    other_participant = conversation.worker if user == conversation.client else conversation.client
    
    if BlockedUser.objects.filter(
        Q(blocker=user, blocked=other_participant) |
        Q(blocker=other_participant, blocked=user)
    ).exists():
        return Response(
            {'error': 'Impossible d\'envoyer un message à cet utilisateur'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # ✅ إعادة تفعيل المحادثة مع الحفاظ على تاريخ الحذف
    if user == conversation.client:
        # إذا العميل هو المرسل، أعد تفعيلها له واحذف التاريخ (يرى كل الرسائل)
        if conversation.deleted_by_client:
            conversation.deleted_by_client = False
            conversation.deleted_at_by_client = None
        # العامل: فقط أعد التفعيل دون حذف التاريخ
        if conversation.deleted_by_worker:
            conversation.deleted_by_worker = False
            # ⚠️ نترك deleted_at_by_worker كما هو
    else:
        # إذا العامل هو المرسل، أعد تفعيلها له واحذف التاريخ (يرى كل الرسائل)
        if conversation.deleted_by_worker:
            conversation.deleted_by_worker = False
            conversation.deleted_at_by_worker = None
        # العميل: فقط أعد التفعيل دون حذف التاريخ
        if conversation.deleted_by_client:
            conversation.deleted_by_client = False
            # ✅ نترك deleted_at_by_client كما هو (هذا السطر هو المهم!)

    conversation.save()

    serializer = SendMessageSerializer(data=request.data)
    
    if serializer.is_valid():
        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=serializer.validated_data['content']
            )
        
        response_serializer = MessageSerializer(message, context={'request': request})
                
                # ✅ إشعار المستلم برسالة جديدة
        recipient = conversation.worker if user == conversation.client else conversation.client
        from notifications.utils import notify_message_received
        notify_message_received(
                    recipient_user=recipient,
                    sender_user=user,
                    task=conversation.task if hasattr(conversation, 'task') else None,
                    message_preview=message.content[:50]
                )
                
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
    user = request.user
    
    if user not in [conversation.client, conversation.worker]:
        return Response(
            {'error': 'Vous n\'êtes pas participant à cette conversation'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # ✅ حذف من جهة المستخدم مع حفظ التاريخ
    if user == conversation.client:
        conversation.deleted_by_client = True
        conversation.deleted_at_by_client = timezone.now()
    else:
        conversation.deleted_by_worker = True
        conversation.deleted_at_by_worker = timezone.now()
    
    # ✅ إذا حذفها الطرفان، احذفها نهائياً
    if conversation.deleted_by_client and conversation.deleted_by_worker:
        conversation.delete()
    else:
        conversation.save()
    
    return Response({'message': 'Conversation supprimée avec succès'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_messages_count(request):
    """
    عدد الرسائل غير المقروءة الإجمالي
    GET /api/chat/unread-count/
    """
    user = request.user
    
    conversations = Conversation.objects.filter(
        Q(client=user) | Q(worker=user),
        is_active=True
    )
    
    total_unread = 0
    for conversation in conversations:
        total_unread += conversation.get_unread_count(user)
    
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
            reporter=self.request.user
        ).select_related('reported_user', 'conversation')


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
    user = request.user
    
    try:
        blocked_user = BlockedUser.objects.get(
            blocker=user,
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
    user = request.user
    
    blocked_users = BlockedUser.objects.filter(
        blocker=user
    ).select_related('blocked')
    
    data = []
    for block in blocked_users:
        data.append({
            'id': block.blocked.id,
            'full_name': block.blocked.get_full_name() or block.blocked.username,
            'role': block.blocked.role,
            'reason': block.reason,
            'blocked_at': block.created_at
        })
    
    return Response({'blocked_users': data})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_conversation(request):
    """
    بدء محادثة جديدة أو إرجاع محادثة موجودة
    Start new conversation or return existing one
    POST /api/chat/start-conversation/
    """
    other_user_id = request.data.get('other_user_id')
    initial_message = request.data.get('initial_message', '')
    
    # التحقق من صحة البيانات
    if not other_user_id:
        return Response(
            {'error': 'other_user_id est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # التحقق من وجود المستخدم الآخر
    try:
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    current_user = request.user
    
    # التحقق من عدم محاولة إنشاء محادثة مع النفس
    if current_user.id == other_user.id:
        return Response(
            {'error': 'Impossible de créer une conversation avec vous-même'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # التحقق من الأدوار (عميل مع عامل فقط)
    if (current_user.role == other_user.role):
        return Response(
            {'error': 'Conversations uniquement entre clients et prestataires'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # تحديد من هو العميل ومن هو العامل
    if current_user.role == 'client':
        client = current_user
        worker = other_user
    else:
        client = other_user
        worker = current_user
    
    # التحقق من عدم وجود حظر متبادل
    if BlockedUser.objects.filter(
        Q(blocker=current_user, blocked=other_user) |
        Q(blocker=other_user, blocked=current_user)
    ).exists():
        return Response(
            {'error': 'Impossible de créer une conversation avec cet utilisateur'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # البحث عن محادثة موجودة أو إنشاء جديدة
    conversation, created = Conversation.objects.get_or_create(
        client=client,
        worker=worker,
        defaults={'is_active': True}
    )
    
    # إذا كانت المحادثة موجودة لكن غير نشطة، فعّلها
    if not created and not conversation.is_active:
        conversation.is_active = True
        conversation.save()
    
    # إرسال الرسالة الأولى إذا تم توفيرها
    first_message = None
    if initial_message and initial_message.strip():
        with transaction.atomic():
            first_message = Message.objects.create(
                conversation=conversation,
                sender=current_user,
                content=initial_message.strip()
            )
            # ✅ إشعار المستلم برسالة جديدة
        from notifications.utils import notify_message_received
        notify_message_received(
            recipient_user=other_user,
            sender_user=current_user,
            task=conversation.task if hasattr(conversation, 'task') else None,
            message_preview=first_message.content[:50]
        )
            
    # تحضير معلومات المستخدم الآخر
    other_user_data = {
        'id': other_user.id,
        'full_name': other_user.get_full_name() or other_user.username,
        'role': other_user.role,
        'profile_image_url': None,
        'is_online': False
    }
    
    # إضافة صورة الملف الشخصي إذا توفرت
    if hasattr(other_user, 'client_profile') and other_user.client_profile.profile_image:
        other_user_data['profile_image_url'] = request.build_absolute_uri(
            other_user.client_profile.profile_image.url
        )
    elif hasattr(other_user, 'worker_profile') and other_user.worker_profile.profile_image:
        other_user_data['profile_image_url'] = request.build_absolute_uri(
            other_user.worker_profile.profile_image.url
        )
    
    # تحديد حالة الاتصال
    if other_user.last_login:
        time_diff = timezone.now() - other_user.last_login
        other_user_data['is_online'] = time_diff.total_seconds() < 300  # 5 دقائق
    
    response_data = {
        'conversation_id': conversation.id,
        'is_new': created,
        'other_user': other_user_data,
        'conversation_active': conversation.is_active
    }
    
    # إضافة معلومات الرسالة الأولى إذا تم إرسالها
    if first_message:
        response_data['first_message'] = {
            'id': first_message.id,
            'content': first_message.content,
            'created_at': first_message.created_at
        }
    
    return Response(response_data, status=status.HTTP_200_OK)