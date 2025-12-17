"""
Signal لزيادة عداد المهام تلقائياً
النظام الجديد: يدعم المهام المجانية + حزم المهام المدفوعة
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from tasks.models import ServiceRequest
from payments.models import UserTaskCounter


@receiver(post_save, sender=ServiceRequest)
def increment_task_counter_on_accept(sender, instance, created, **kwargs):
    """
    زيادة عداد المهام تلقائياً عند قبول العامل
    
    الشروط:
    1. حالة المهمة = 'active'
    2. يوجد عامل مقبول (assigned_worker)
    
    يزيد العداد للطرفين:
    - العميل (client)
    - العامل المقبول (assigned_worker)
    
    المنطق الجديد:
    - إذا المستخدم في الفترة المجانية → يزيد free_tasks_used
    - إذا المستخدم لديه حزمة نشطة → يزيد tasks_used في الحزمة
    """
    
    # ✅ فقط إذا المهمة نشطة وعامل مقبول
    if instance.status == 'active' and instance.assigned_worker:
        
        task_id = instance.id  # ID المهمة الفريد
        
        # ================================
        # 1️⃣ زيادة عداد العميل
        # ================================
        client_counter, _ = UserTaskCounter.objects.get_or_create(
            user=instance.client
        )
        
        client_counter.increment_counter(task_id)
        
        # ================================
        # 2️⃣ زيادة عداد العامل
        # ================================
        worker_counter, _ = UserTaskCounter.objects.get_or_create(
            user=instance.assigned_worker
        )
        
        worker_counter.increment_counter(task_id)