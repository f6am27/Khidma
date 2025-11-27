# payments/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Sum, Count, Avg
from django.shortcuts import get_object_or_404
from payments.models import Payment
from .moosyl_service import moosyl_service
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json
from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PaymentCreateSerializer,
    PaymentStatisticsSerializer,
)
from tasks.models import ServiceRequest


class PaymentListCreateView(generics.ListCreateAPIView):
    """
    List and create payments
    GET: List payments
    POST: Create new payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get payments for authenticated user"""
        user = self.request.user
        
        # Clients see payments they made
        if user.role == 'client':
            return Payment.objects.filter(payer=user).select_related(
                'task', 'payer', 'receiver', 'task__service_category'
            )
        
        # Workers see payments they received
        elif user.role == 'worker':
            return Payment.objects.filter(receiver=user).select_related(
                'task', 'payer', 'receiver', 'task__service_category'
            )
        
        return Payment.objects.none()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentCreateSerializer
        return PaymentListSerializer
    
    def perform_create(self, serializer):
        """Create payment from task completion"""
        payment = serializer.save()
        print(f'✅ Payment created: {payment.id} - Amount: {payment.amount}')
        
        # ✅ إشعار العميل بالدفع
        from notifications.utils import notify_payment_received
        notify_payment_received(
            client_user=payment.payer,
            task=payment.task,
            amount=payment.amount
        )
        
        # ✅ إشعار العامل باستلام الدفع
        from notifications.utils import notify_payment_sent
        notify_payment_sent(
            worker_user=payment.receiver,
            task=payment.task,
            amount=payment.amount
        )

class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """User can only access their own payments"""
        user = self.request.user
        
        if user.role == 'client':
            return Payment.objects.filter(payer=user)
        elif user.role == 'worker':
            return Payment.objects.filter(receiver=user)
        
        return Payment.objects.none()
    
    def perform_update(self, serializer):
        """Update payment status"""
        payment = serializer.save()
        
        if payment.status == 'completed':
            print(f'✅ Payment {payment.id} completed')
            
            # ✅ إشعار العميل بإتمام الدفع
            from notifications.utils import notify_payment_received
            notify_payment_received(
                client_user=payment.payer,
                task=payment.task,
                amount=payment.amount
            )
            
            # ✅ إشعار العامل باستلام الدفع
            from notifications.utils import notify_payment_sent
            notify_payment_sent(
                worker_user=payment.receiver,
                task=payment.task,
                amount=payment.amount
            )
            
class MyPaymentsView(generics.ListAPIView):
    """
    Get my payments (made or received)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        return PaymentListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'client':
            return Payment.objects.filter(payer=user).select_related(
                'task', 'receiver', 'task__service_category'
            ).order_by('-created_at')
        
        elif user.role == 'worker':
            return Payment.objects.filter(receiver=user).select_related(
                'task', 'payer', 'task__service_category'
            ).order_by('-created_at')
        
        return Payment.objects.none()


class ReceivedPaymentsView(generics.ListAPIView):
    """
    Get payments received (for workers only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentListSerializer
    
    def get_queryset(self):
        if self.request.user.role != 'worker':
            raise PermissionDenied("Only workers can view received payments")
        
        return Payment.objects.filter(
            receiver=self.request.user,
            status='completed'
        ).select_related(
            'task', 'payer', 'task__service_category'
        ).order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_statistics(request):
    """
    Get payment statistics for authenticated user
    """
    user = request.user
    
    if user.role == 'client':
        # Client statistics - payments made
        payments = Payment.objects.filter(payer=user)
        
        total_amount = payments.filter(
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        stats = {
            'role': 'client',
            'total_paid': float(total_amount),
            'total_transactions': payments.count(),
            'completed': payments.filter(status='completed').count(),
            'pending': payments.filter(status='pending').count(),
            'cancelled': payments.filter(status='cancelled').count(),
            'average_per_transaction': float(
                payments.filter(
                    status='completed'
                ).aggregate(Avg('amount'))['amount__avg'] or 0
            ),
            'payment_methods': dict(
                payments.values('payment_method').annotate(
                    count=Count('id')
                ).values_list('payment_method', 'count')
            ),
        }
    
    elif user.role == 'worker':
        # Worker statistics - payments received
        payments = Payment.objects.filter(receiver=user)
        
        total_amount = payments.filter(
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        stats = {
            'role': 'worker',
            'total_earned': float(total_amount),
            'total_transactions': payments.count(),
            'completed': payments.filter(status='completed').count(),
            'pending': payments.filter(status='pending').count(),
            'cancelled': payments.filter(status='cancelled').count(),
            'average_per_transaction': float(
                payments.filter(
                    status='completed'
                ).aggregate(Avg('amount'))['amount__avg'] or 0
            ),
            'payment_methods': dict(
                payments.values('payment_method').annotate(
                    count=Count('id')
                ).values_list('payment_method', 'count')
            ),
        }
    
    else:
        stats = {'error': 'Invalid user role'}
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_history(request):
    """
    Get complete payment history with filters
    Query params: status, payment_method, limit, offset
    """
    user = request.user
    
    # Get base queryset
    if user.role == 'client':
        queryset = Payment.objects.filter(payer=user)
    elif user.role == 'worker':
        queryset = Payment.objects.filter(receiver=user)
    else:
        queryset = Payment.objects.none()
    
    # Apply filters
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    payment_method = request.query_params.get('payment_method')
    if payment_method:
        queryset = queryset.filter(payment_method=payment_method)
    
    # Order by date
    queryset = queryset.order_by('-created_at').select_related(
        'task', 'payer', 'receiver', 'task__service_category'
    )
    
    # Pagination
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    total_count = queryset.count()
    paginated = queryset[offset:offset + limit]
    
    serializer = PaymentListSerializer(paginated, many=True)
    
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data,
    }, status=status.HTTP_200_OK)


class InitiateMoosylPaymentView(APIView):
    """
    إنشاء طلب دفع إلكتروني عبر Moosyl
    POST: /api/payments/moosyl/initiate/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # التحقق من أن المستخدم عميل
        if user.role != 'client':
            return Response(
                {'error': 'Seuls les clients peuvent effectuer des paiements'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # الحصول على البيانات
        task_id = request.data.get('task_id')
        payment_method = request.data.get('payment_method', 'bankily').lower()
        amount = request.data.get('amount')
        
        # التحقق من صحة البيانات
        if not task_id or not amount:
            return Response(
                {'error': 'task_id et amount sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # التحقق من طريقة الدفع
        valid_methods = ['bankily', 'sedad', 'masrivi']
        if payment_method not in valid_methods:
            return Response(
                {'error': f'Méthode invalide. Utilisez: {", ".join(valid_methods)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # الحصول على المهمة
            task = ServiceRequest.objects.get(id=task_id)
            
            # التحقق من أن المستخدم هو عميل المهمة
            if task.client != user:
                return Response(
                    {'error': 'Vous n\'êtes pas le client de cette tâche'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # التحقق من أن المهمة مكتملة
            if task.status != 'work_completed':
                return Response(
                    {'error': 'Le travailleur doit terminer le travail d\'abord'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # التحقق من عدم وجود دفع سابق
            if hasattr(task, 'payment') and task.payment.is_completed:
                return Response(
                    {'error': 'Cette tâche a déjà été payée'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # إنشاء أو تحديث سجل الدفع
            payment, created = Payment.objects.get_or_create(
                task=task,
                defaults={
                    'payer': user,
                    'receiver': task.assigned_worker,
                    'amount': amount,
                    'payment_method': payment_method,
                    'status': 'pending',
                }
            )
            
            if not created and payment.is_completed:
                return Response(
                    {'error': 'Cette tâche a déjà été payée'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # إنشاء معرف فريد للمعاملة
            transaction_id = f"TASK-{task.id}-PAY-{payment.id}"
            
            # إنشاء طلب دفع في Moosyl
            moosyl_result = moosyl_service.create_payment_request(
                amount=amount,
                transaction_id=transaction_id,
                phone_number=user.phone,  # ✅ إرسال رقم العميل
            )
            
            if not moosyl_result.get('success'):
                payment.mark_as_failed(reason=moosyl_result.get('error'))
                return Response(
                    {
                        'error': 'Échec de l\'initialisation du paiement',
                        'details': moosyl_result.get('message')
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # تحديث معلومات الدفع
            payment.moosyl_transaction_id = moosyl_result.get('transaction_id')
            payment.moosyl_response = moosyl_result.get('data')
            payment.status = 'processing'
            payment.save()
            
            # بناء رابط الدفع للـ Frontend
            from django.conf import settings
            publishable_key = settings.MOOSYL_PUBLISHABLE_KEY
            
            return Response({
                'success': True,
                'payment_id': payment.id,
                'transaction_id': payment.moosyl_transaction_id,
                'publishable_key': publishable_key,
                'amount': float(amount),
                'message': 'Paiement initialisé avec succès',
            }, status=status.HTTP_201_CREATED)
        
        except ServiceRequest.DoesNotExist:
            return Response(
                {'error': 'Tâche non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyMoosylPaymentView(APIView):
    """
    التحقق من حالة الدفع
    GET: /api/payments/moosyl/verify/<payment_id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, payment_id):
        try:
            # الحصول على الدفع
            payment = Payment.objects.get(id=payment_id)
            
            # التحقق من الصلاحية
            if payment.payer != request.user and payment.receiver != request.user:
                return Response(
                    {'error': 'Non autorisé'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # إذا كان الدفع مكتملاً مسبقاً
            if payment.is_completed:
                return Response({
                    'status': 'completed',
                    'message': 'Paiement déjà complété',
                    'payment': PaymentSerializer(payment).data
                })
            
            # التحقق من Moosyl
            if payment.moosyl_transaction_id:
                moosyl_result = moosyl_service.verify_payment(
                    payment.moosyl_transaction_id
                )
                
                if moosyl_result.get('success'):
                    moosyl_status = moosyl_result.get('status')
                    
                    # تحديث حالة الدفع حسب حالة Moosyl
                    if moosyl_status == 'paid':
                        payment.mark_as_completed()
                        
                        # تحديث حالة المهمة إلى مكتملة
                        task = payment.task
                        task.status = 'completed'
                        task.save()
                        
                        # إرسال إشعارات
                        from notifications.utils import notify_payment_received, notify_payment_sent
                        notify_payment_received(payment.payer, payment.task, payment.amount)
                        notify_payment_sent(payment.receiver, payment.task, payment.amount)
                        
                        
                        return Response({
                            'status': 'completed',
                            'message': 'Paiement complété avec succès',
                            'payment': PaymentSerializer(payment).data
                        })
                    elif moosyl_status == 'cancelled':
                        payment.mark_as_failed(reason="Paiement annulé")
                        return Response({
                            'status': 'failed',
                            'message': 'Le paiement a été annulé',
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    else:
                        # pending ou processing
                        return Response({
                            'status': moosyl_status,
                            'message': 'Paiement en cours',
                        })
            
            return Response({
                'status': payment.status,
                'message': 'État du paiement',
            })
        
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Paiement non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )


@csrf_exempt
@api_view(['POST'])
@permission_classes([])
def moosyl_webhook(request):
    """
    Webhook لاستقبال إشعارات Moosyl
    POST: /api/payments/moosyl/webhook/
    """
    try:
        # الحصول على البيانات
        payload = json.loads(request.body)
        event = request.headers.get('X-Webhook-Event', '')
        
        print(f"🔔 Webhook received: {event}")
        print(f"📦 Payload: {payload}")
        
        if event == 'payment-created':
            transaction_id = payload.get('data', {}).get('id')
            
            if not transaction_id:
                return JsonResponse({'error': 'Transaction ID manquant'}, status=400)
            
            # العثور على الدفع
            try:
                payment = Payment.objects.get(moosyl_transaction_id=transaction_id)
            except Payment.DoesNotExist:
                return JsonResponse({'error': 'Paiement non trouvé'}, status=404)
            
            # تحديث حالة الدفع إلى مكتمل
            payment.mark_as_completed()
            
            # إرسال إشعارات
            from notifications.utils import notify_payment_received, notify_payment_sent
            notify_payment_received(payment.payer, payment.task, payment.amount)
            notify_payment_sent(payment.receiver, payment.task, payment.amount)
            
            print(f"✅ Payment {payment.id} marked as completed")
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)