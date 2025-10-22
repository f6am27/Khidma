# payments/serializers.py
from rest_framework import serializers
from .models import Payment
from users.models import User
from tasks.models import ServiceRequest


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.phone


class PaymentSerializer(serializers.ModelSerializer):
    """تفصيل كامل لمعاملة الدفع"""
    payer_info = UserBasicSerializer(source='payer', read_only=True)
    receiver_info = UserBasicSerializer(source='receiver', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    service_type = serializers.CharField(
        source='task.service_category.name',
        read_only=True
    )
    payment_method_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'task',
            'task_title',
            'service_type',
            'amount',
            'payment_method',
            'payment_method_display',
            'transaction_id',
            'status',
            'payer_info',
            'receiver_info',
            'notes',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'completed_at',
            'payer_info',
            'receiver_info',
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """قائمة الدفعات (بيانات مختصرة)"""
    payer_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    task_title = serializers.CharField(source='task.title', read_only=True)
    service_type = serializers.CharField(
        source='task.service_category.name',
        read_only=True
    )
    payment_method_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'task_title',
            'service_type',
            'amount',
            'payment_method',
            'payment_method_display',
            'status',
            'payer_name',
            'receiver_name',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_payer_name(self, obj):
        return obj.payer.get_full_name() or obj.payer.phone
    
    def get_receiver_name(self, obj):
        return obj.receiver.get_full_name() or obj.receiver.phone


class PaymentCreateSerializer(serializers.ModelSerializer):
    """إنشاء معاملة دفع جديدة"""
    
    class Meta:
        model = Payment
        fields = [
            'task',
            'payer',
            'receiver',
            'amount',
            'payment_method',
            'transaction_id',
            'notes',
        ]
    
    def validate(self, data):
        task = data.get('task')
        payer = data.get('payer')
        receiver = data.get('receiver')
        
        # التحقق من أن المهمة موجودة
        if not task:
            raise serializers.ValidationError("Task is required")
        
        # التحقق من أن payer هو عميل
        if payer.role != 'client':
            raise serializers.ValidationError("Payer must be a client")
        
        # التحقق من أن receiver هو عامل
        if receiver.role != 'worker':
            raise serializers.ValidationError("Receiver must be a worker")
        
        # التحقق من أن payer هو عميل المهمة
        if task.client != payer:
            raise serializers.ValidationError(
                "Payer must be the task client"
            )
        
        # التحقق من أن receiver هو العامل المعين للمهمة
        if task.assigned_worker != receiver:
            raise serializers.ValidationError(
                "Receiver must be the assigned worker"
            )
        
        return data
    
    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data)
        return payment


class PaymentStatisticsSerializer(serializers.Serializer):
    """إحصائيات الدفع"""
    total_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)
    cancelled_count = serializers.IntegerField(read_only=True)
    average_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    payment_methods = serializers.DictField(read_only=True)