# payments/views.py
"""
APIs نظام عداد المهام والاشتراكات
✅ تم التفعيل: التحقق من الحد، عرض الإحصائيات
🔮 معطل: الدفع (ينتظر ربط Benkily)
"""

from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models  

from .models import UserTaskCounter, PlatformSubscription
from .serializers import (
    UserTaskCounterSerializer,
    UserTaskCounterSimpleSerializer,
    PlatformSubscriptionSerializer,
    SubscriptionCreateSerializer
)


# ================================
# 1️⃣ التحقق من حد المهام
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_task_limit(request):
    """
    ✅ التحقق من عدد المهام المتبقية للمستخدم
    
    Response:
    {
        "accepted_tasks_count": 3,
        "tasks_remaining": 2,
        "needs_subscription": false,
        "is_premium": false,
        "status": {...},
        "message": "..."
    }
    """
    counter, created = UserTaskCounter.objects.get_or_create(
        user=request.user
    )
    
    serializer = UserTaskCounterSimpleSerializer(counter)
    
    # رسالة للمستخدم
    FREE_LIMIT = 5
    remaining = FREE_LIMIT - counter.accepted_tasks_count
    
    if counter.is_premium:
        message = "✅ أنت مشترك - لا حدود!"
        message_fr = "✅ Vous êtes abonné - Illimité!"
        status_type = "premium"
    elif remaining > 0:
        message = f"✅ متبقي {remaining} مهام مجانية"
        message_fr = f"✅ {remaining} tâches gratuites restantes"
        status_type = "active"
    else:
        message = "⚠️ استنفدت الحد المجاني (5 مهام). يرجى الاشتراك."
        message_fr = "⚠️ Limite atteinte (5 tâches). Veuillez vous abonner."
        status_type = "limit_reached"
    
    return Response({
        **serializer.data,
        'status': {
            'type': status_type,
            'message': message,
            'message_fr': message_fr
        },
        'subscription': {
            'required': counter.needs_payment,
            'monthly_price': '8 MRU',
            'duration': '30 jours'
        }
    })


# ================================
# 2️⃣ عرض تفاصيل العداد
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_task_counter(request):
    """
    ✅ عرض تفاصيل كاملة عن عداد المهام
    """
    counter, created = UserTaskCounter.objects.get_or_create(
        user=request.user
    )
    
    serializer = UserTaskCounterSerializer(counter)
    return Response(serializer.data)


# ================================
# 3️⃣ إحصائيات للـ Admin
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_counter_stats(request):
    """
    ✅ إحصائيات عامة (للـ Admin فقط)
    """
    # التحقق من صلاحيات Admin
    if not request.user.is_staff and not request.user.is_superuser:
        return Response({
            'error': 'صلاحيات غير كافية',
            'error_fr': 'Permissions insuffisantes'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Count, Sum, Avg
    
    stats = UserTaskCounter.objects.aggregate(
        total_users=Count('id'),
        total_tasks=Sum('accepted_tasks_count'),
        avg_tasks_per_user=Avg('accepted_tasks_count'),
        premium_users=Count('id', filter=models.Q(is_premium=True)),
        users_at_limit=Count('id', filter=models.Q(accepted_tasks_count__gte=5, is_premium=False))
    )
    
    return Response({
        'statistics': stats,
        'free_limit': 5,
        'subscription_price': '8 MRU/mois'
    })


# ================================
# 4️⃣ بدء الاشتراك (معطل - ينتظر Benkily)
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_subscription(request):
    """
    🔮 بدء عملية الاشتراك الشهري
    ❌ معطل حالياً - ينتظر ربط Benkily API
    """
    counter, created = UserTaskCounter.objects.get_or_create(
        user=request.user
    )
    
    # التحقق من الحاجة للاشتراك
    if not counter.needs_payment and not request.user.is_staff:
        return Response({
            'error': 'لا تحتاج للاشتراك حالياً',
            'error_fr': 'Pas besoin d\'abonnement pour le moment',
            'tasks_remaining': counter.tasks_remaining_before_payment
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 🔮 هنا سيتم إضافة كود Benkily لاحقاً
    return Response({
        'message': 'نظام الدفع قيد التطوير',
        'message_fr': 'Système de paiement en développement',
        'subscription_details': {
            'amount': '8 MRU',
            'currency': 'MRU',
            'duration': '30 jours',
            'payment_method': 'Benkily (قريباً)'
        },
        'note': 'يرجى التواصل مع الدعم الفني لتفعيل الاشتراك يدوياً'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


# ================================
# 5️⃣ تأكيد الدفع (Webhook - للمستقبل)
# ================================

@api_view(['POST'])
def benkily_webhook(request):
    """
    🔮 Webhook لاستقبال إشعارات الدفع من Benkily
    ❌ معطل حالياً
    """
    # 🔮 هنا سيتم معالجة Webhook من Benkily
    return Response({
        'message': 'Webhook غير مفعل حالياً'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


# ================================
# 6️⃣ تاريخ الاشتراكات
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscriptions(request):
    """
    ✅ عرض تاريخ الاشتراكات للمستخدم
    """
    subscriptions = PlatformSubscription.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    serializer = PlatformSubscriptionSerializer(subscriptions, many=True)
    
    return Response({
        'count': subscriptions.count(),
        'subscriptions': serializer.data
    })


# ================================
# 7️⃣ تفعيل اشتراك يدوياً (Admin فقط)
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activate_subscription_manual(request, user_id):
    """
    ✅ تفعيل اشتراك يدوياً (للـ Admin فقط)
    """
    # التحقق من صلاحيات Admin
    if not request.user.is_staff and not request.user.is_superuser:
        return Response({
            'error': 'صلاحيات غير كافية'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from django.utils import timezone
    from datetime import timedelta
    from users.models import User
    
    # الحصول على المستخدم
    target_user = get_object_or_404(User, id=user_id)
    
    # الحصول على أو إنشاء العداد
    counter, created = UserTaskCounter.objects.get_or_create(
        user=target_user
    )
    
    # تفعيل Premium
    counter.is_premium = True
    counter.last_payment_date = timezone.now()
    counter.save()
    
    # إنشاء سجل اشتراك
    subscription = PlatformSubscription.objects.create(
        user=target_user,
        amount=800.00,  # 8 MRU
        payment_method='other',
        status='completed',
        transaction_id=f'MANUAL-{timezone.now().timestamp()}',
        valid_until=timezone.now() + timedelta(days=30)
    )
    
    return Response({
        'message': f'✅ تم تفعيل اشتراك {target_user.phone} بنجاح',
        'subscription': PlatformSubscriptionSerializer(subscription).data,
        'counter': UserTaskCounterSerializer(counter).data
    })


# ================================
# 8️⃣ إعادة تعيين العداد (Admin فقط)
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_counter_manual(request, user_id):
    """
    ✅ إعادة تعيين العداد يدوياً (للـ Admin فقط)
    """
    # التحقق من صلاحيات Admin
    if not request.user.is_staff and not request.user.is_superuser:
        return Response({
            'error': 'صلاحيات غير كافية'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from users.models import User
    
    # الحصول على المستخدم
    target_user = get_object_or_404(User, id=user_id)
    
    # الحصول على العداد
    counter = get_object_or_404(UserTaskCounter, user=target_user)
    
    # إعادة تعيين
    counter.reset_counter()
    
    return Response({
        'message': f'✅ تم إعادة تعيين عداد {target_user.phone} بنجاح',
        'counter': UserTaskCounterSerializer(counter).data
    })


# ================================
# 9️⃣ API قديمة معطلة
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_system_disabled(request):
    """
    ✅ إشعار بأن نظام الدفع بين العميل والعامل معطل
    """
    return Response({
        'message': 'نظام الدفع بين العميل والعامل معطل',
        'message_fr': 'Le système de paiement entre client et travailleur est désactivé',
        'note': 'العمل يتم خارج التطبيق بعد قبول العامل',
        'note_fr': 'Le travail se fait en dehors de l\'application après acceptation',
        'new_system': {
            'name': 'نظام عداد المهام',
            'name_fr': 'Système de compteur de tâches',
            'limit': '5 مهام مجانية',
            'subscription': '8 MRU/شهر',
            'api': '/api/payments/check-limit/'
        }
    }, status=status.HTTP_200_OK)