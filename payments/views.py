# payments/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Sum, Count, Avg
from django.shortcuts import get_object_or_404
from payments.models import Payment

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