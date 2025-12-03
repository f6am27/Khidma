
"""
Signal لزيادة عداد المهام تلقائياً
يستخدم نظام تتبع IDs لمنع الحساب المزدوج
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
    3. المهمة لم يتم حسابها من قبل (باستخدام task ID)
    
    يزيد العداد للطرفين:
    - العميل (client)
    - العامل المقبول (assigned_worker)
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
        
        # هل تم حساب هذه المهمة للعميل من قبل؟
        if task_id not in client_counter.counted_task_ids:
            client_counter.increment_counter()
            client_counter.counted_task_ids.append(task_id)
            client_counter.save()
            
            print(f"✅ Client counter increased: {instance.client.phone} - Task #{task_id}")
        else:
            print(f"⏭️ Task #{task_id} already counted for client {instance.client.phone}")
        
        # ================================
        # 2️⃣ زيادة عداد العامل
        # ================================
        worker_counter, _ = UserTaskCounter.objects.get_or_create(
            user=instance.assigned_worker
        )
        
        # هل تم حساب هذه المهمة للعامل من قبل؟
        if task_id not in worker_counter.counted_task_ids:
            worker_counter.increment_counter()
            worker_counter.counted_task_ids.append(task_id)
            worker_counter.save()
            
            print(f"✅ Worker counter increased: {instance.assigned_worker.phone} - Task #{task_id}")
        else:
            print(f"⏭️ Task #{task_id} already counted for worker {instance.assigned_worker.phone}")


# ================================
# Signal بديل (اختياري): استخدام pre_save للتحقق من التغييرات
# ================================
# from django.db.models.signals import pre_save

# @receiver(pre_save, sender=ServiceRequest)
# def track_status_change(sender, instance, **kwargs):
#     """
#     تتبع تغيير حالة المهمة من pending → active
#     (هذا Signal اختياري - يمكن استخدامه بدلاً من post_save)
#     """
#     if instance.pk:  # إذا المهمة موجودة (ليست جديدة)
#         try:
#             old_instance = ServiceRequest.objects.get(pk=instance.pk)
#             # إذا تغيرت الحالة من pending → active
#             if old_instance.status != 'active' and instance.status == 'active':
#                 instance._status_changed_to_active = True
#         except ServiceRequest.DoesNotExist:
#             pass
