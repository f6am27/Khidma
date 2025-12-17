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
from decimal import Decimal
from .models import UserTaskCounter, PlatformSubscription
from .serializers import * 


# ================================
# 1️⃣ التحقق من حد المهام
# ================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_task_limit(request):
    """
    ✅ التحقق من عدد المهام المتبقية للمستخدم - النظام الجديد
    
    Response:
    {
        "current_usage": 3,
        "current_limit": 8,
        "tasks_remaining": 5,
        "needs_subscription": false,
        "status": {...},
        "bundle_info": {...}
    }
    """
    counter, created = UserTaskCounter.objects.get_or_create(
        user=request.user
    )
    
    serializer = UserTaskCounterSerializer(counter)
    
    # رسالة للمستخدم
    active_bundle = counter.get_active_bundle()
    remaining = counter.tasks_remaining
    
    if active_bundle:
        message = f"✅ لديك {remaining} مهام متبقية في الحزمة"
        message_fr = f"✅ Il vous reste {remaining} tâches dans le bundle"
        status_type = "active_bundle"
    elif counter.free_tasks_used < 5:
        message = f"✅ متبقي {remaining} مهام مجانية"
        message_fr = f"✅ {remaining} tâches gratuites restantes"
        status_type = "free_period"
    else:
        message = "⚠️ يجب شراء حزمة جديدة (8 مهام بـ 5 أوقيات)"
        message_fr = "⚠️ Achat de bundle requis (8 tâches pour 5 MRU)"
        status_type = "limit_reached"
    
    return Response({
        **serializer.data,
        'status': {
            'type': status_type,
            'message': message,
            'message_fr': message_fr
        },
        'bundle_pricing': {
            'tasks': 8,
            'price': '5 MRU',
            'price_per_task': '0.625 MRU'
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
    ✅ إحصائيات عامة - النظام الجديد (للـ Admin فقط)
    """
    # التحقق من صلاحيات Admin
    if not request.user.is_staff and not request.user.is_superuser:
        return Response({
            'error': 'صلاحيات غير كافية',
            'error_fr': 'Permissions insuffisantes'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Count, Sum, Avg
    from payments.models import TaskBundle
    
    # إحصائيات المستخدمين
    user_stats = UserTaskCounter.objects.aggregate(
        total_users=Count('id'),
        users_in_free_period=Count('id', filter=models.Q(free_tasks_used__lt=5, total_subscriptions=0)),
        users_subscribed_once=Count('id', filter=models.Q(total_subscriptions=1)),
        users_subscribed_multiple=Count('id', filter=models.Q(total_subscriptions__gte=2)),
        avg_subscriptions_per_user=Avg('total_subscriptions'),
    )
    
    # إحصائيات الحزم
    bundle_stats = TaskBundle.objects.aggregate(
        total_bundles_sold=Count('id', filter=models.Q(moosyl_payment_status='completed')),
        total_bundles_active=Count('id', filter=models.Q(is_active=True, moosyl_payment_status='completed')),
        total_bundles_exhausted=Count('id', filter=models.Q(is_active=False, moosyl_payment_status='completed')),
        total_tasks_in_bundles=Sum('tasks_used', filter=models.Q(moosyl_payment_status='completed')),
    )
    
    # الإيرادات
    total_revenue = bundle_stats['total_bundles_sold'] * 5 if bundle_stats['total_bundles_sold'] else 0
    
    return Response({
        'user_statistics': user_stats,
        'bundle_statistics': bundle_stats,
        'revenue': {
            'total_mru': total_revenue,
            'currency': 'MRU',
            'bundles_sold': bundle_stats['total_bundles_sold'],
        },
        'pricing': {
            'free_tasks': 5,
            'bundle_tasks': 8,
            'bundle_price': '5 MRU'
        }
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

# ================================
# 🚀 Moosyl Integration - شراء الحزم
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_bundle(request):
    """
    ✅ بدء عملية شراء حزمة جديدة (8 مهام بـ 5 أوقيات)
    
    Flow:
    1. التحقق من أن المستخدم يحتاج للشراء
    2. إنشاء سجل TaskBundle بحالة 'pending'
    3. إنشاء payment request في Moosyl
    4. إرجاع transaction_id للـ Frontend
    
    Response:
    {
        "success": true,
        "transaction_id": "moosyl_txn_123...",
        "bundle_id": 1,
        "amount": 5.00,
        "publishable_key": "pk_test_...",
        "message": "..."
    }
    """
    from payments.utils import get_moosyl_client
    from payments.models import TaskBundle
    import uuid
    
    # 1️⃣ التحقق من الحاجة للشراء
    counter, _ = UserTaskCounter.objects.get_or_create(user=request.user)
    
    if not counter.needs_payment:
        return Response({
            'success': False,
            'error': 'no_need',
            'message': 'لا تحتاج لشراء حزمة الآن',
            'message_fr': 'Vous n\'avez pas besoin d\'acheter un bundle',
            'tasks_remaining': counter.tasks_remaining
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 2️⃣ إنشاء معرف فريد لهذه المعاملة
    our_transaction_id = f"bundle_{request.user.id}_{uuid.uuid4().hex[:8]}"
    
    # 3️⃣ إنشاء سجل TaskBundle (pending)
    bundle = TaskBundle.objects.create(
        user=request.user,
        bundle_type='paid_8_tasks',
        tasks_included=8,
        tasks_used=0,
        payment_amount=Decimal('5.00'),
        payment_method='moosyl',
        moosyl_transaction_id=our_transaction_id,  # مؤقتاً
        moosyl_payment_status='pending',
        is_active=False  # سيصبح True عند نجاح الدفع
    )
    
    # 4️⃣ إنشاء payment request في Moosyl
    try:
        moosyl = get_moosyl_client()
        
        result = moosyl.create_payment_request(
            amount=5.0,  # 5 أوقيات
            transaction_id=our_transaction_id,
            metadata={
                'user_id': request.user.id,
                'user_phone': request.user.phone,
                'bundle_id': bundle.id,
                'bundle_type': 'paid_8_tasks'
            }
        )
        
        if not result['success']:
            # فشل إنشاء الطلب في Moosyl
            bundle.moosyl_payment_status = 'failed'
            bundle.save()
            
            return Response({
                'success': False,
                'error': 'moosyl_error',
                'message': 'فشل إنشاء طلب الدفع',
                'message_fr': 'Échec de création de la demande de paiement',
                'details': result.get('message')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 5️⃣ تحديث Bundle بـ transaction_id من Moosyl
        bundle.moosyl_transaction_id = result['transaction_id']
        bundle.save()
        
        # 6️⃣ إرجاع البيانات للـ Frontend
        return Response({
            'success': True,
            'transaction_id': result['transaction_id'],  # للـ Flutter
            'bundle_id': bundle.id,
            'amount': float(bundle.payment_amount),
            'currency': 'MRU',
            'publishable_key': moosyl.publishable_key,  # للـ Flutter
            'message': 'تم إنشاء طلب الدفع بنجاح',
            'message_fr': 'Demande de paiement créée avec succès',
            'instructions': {
                'ar': 'استخدم transaction_id في Flutter MoosylView',
                'fr': 'Utilisez transaction_id dans Flutter MoosylView'
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        # خطأ غير متوقع
        bundle.moosyl_payment_status = 'failed'
        bundle.save()
        
        return Response({
            'success': False,
            'error': 'unexpected_error',
            'message': f'خطأ غير متوقع: {str(e)}',
            'message_fr': f'Erreur inattendue: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def moosyl_webhook(request):
    """
    ✅ Webhook من Moosyl - استقبال إشعارات الدفع
    
    Events:
    - payment-created: تم إنشاء الدفع (pending)
    - payment-completed: تم الدفع بنجاح ✅
    - payment-failed: فشل الدفع ❌
    
    Security:
    - التحقق من التوقيع (x-webhook-signature)
    """
    from payments.utils import get_moosyl_client
    from payments.models import TaskBundle
    from django.utils import timezone
    
    # 1️⃣ التحقق من التوقيع
    signature = request.headers.get('x-webhook-signature')
    if not signature:
        return Response({
            'error': 'Missing signature'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    moosyl = get_moosyl_client()
    
    # تحويل request.body إلى bytes إذا لم يكن
    payload = request.body
    
    if not moosyl.verify_webhook_signature(payload, signature):
        return Response({
            'error': 'Invalid signature'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # 2️⃣ قراءة البيانات
    event_type = request.headers.get('x-webhook-event')
    data = request.data
    
    transaction_id = data.get('data', {}).get('id')  # من Moosyl
    our_transaction_id = data.get('data', {}).get('transactionId')  # معرفنا
    
    if not transaction_id or not our_transaction_id:
        return Response({
            'error': 'Missing transaction data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 3️⃣ البحث عن Bundle
    try:
        bundle = TaskBundle.objects.get(
            moosyl_transaction_id__in=[transaction_id, our_transaction_id]
        )
    except TaskBundle.DoesNotExist:
        # Bundle غير موجود - نسجل ونتجاهل
        print(f"⚠️ Webhook for unknown bundle: {transaction_id}")
        return Response({'received': True})
    
    # 4️⃣ معالجة الحدث
    if event_type == 'payment-completed':
        # ✅ الدفع نجح!
        bundle.moosyl_payment_status = 'completed'
        bundle.is_active = True
        bundle.save()
        
        # زيادة عداد الاشتراكات
        counter = bundle.user.task_counter
        counter.total_subscriptions += 1
        counter.save()
        
        print(f"✅ Payment completed: Bundle #{bundle.id} for {bundle.user.phone}")
        
        # TODO: إرسال إشعار للمستخدم
        
    elif event_type == 'payment-failed':
        # ❌ الدفع فشل
        bundle.moosyl_payment_status = 'failed'
        bundle.save()
        
        print(f"❌ Payment failed: Bundle #{bundle.id} for {bundle.user.phone}")
        
    elif event_type == 'payment-created':
        # ℹ️ تم إنشاء الدفع (لا نفعل شيء)
        print(f"ℹ️ Payment created: Bundle #{bundle.id}")
    
    # 5️⃣ إرجاع 200 OK
    return Response({'received': True}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_bundle_status(request, bundle_id):
    """
    ✅ التحقق من حالة حزمة معينة
    """
    bundle = get_object_or_404(TaskBundle, id=bundle_id, user=request.user)
    
    serializer = TaskBundleSerializer(bundle)
    
    return Response({
        'bundle': serializer.data,
        'payment_status': bundle.get_moosyl_payment_status_display(),
        'is_active': bundle.is_active,
        'can_use': bundle.is_active and not bundle.is_exhausted
    })