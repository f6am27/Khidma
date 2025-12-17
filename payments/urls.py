# payments/urls.py
"""
URLs لنظام عداد المهام والاشتراكات
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # ================================
    # 1️⃣ APIs نظام عداد المهام
    # ================================
    
    # التحقق من الحد (للجميع)
    path('check-limit/', views.check_task_limit, name='check_task_limit'),
    
    # عرض تفاصيل العداد (للمستخدم)
    path('my-counter/', views.my_task_counter, name='my_task_counter'),
    
    # إحصائيات (Admin فقط)
    path('stats/', views.task_counter_stats, name='task_counter_stats'),
    
    # ================================
    # 2️⃣ APIs الاشتراكات
    # ================================
    
    # بدء اشتراك (معطل - ينتظر Benkily)
    path('subscribe/', views.initiate_subscription, name='initiate_subscription'),
    
    # تاريخ الاشتراكات
    path('my-subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    
    # Webhook من Benkily (معطل)
    path('benkily/webhook/', views.benkily_webhook, name='benkily_webhook'),
    
    # ================================
    # 3️⃣ APIs Admin (تحكم يدوي)
    # ================================
    
    # تفعيل اشتراك يدوياً
    path('admin/activate/<int:user_id>/', views.activate_subscription_manual, name='activate_subscription_manual'),
    
    # إعادة تعيين العداد
    path('admin/reset/<int:user_id>/', views.reset_counter_manual, name='reset_counter_manual'),
    
    # ================================
    # 4️⃣ API قديمة (للتوافق)
    # ================================
    
    # إشعار بتعطيل نظام الدفع القديم
    path('disabled/', views.payment_system_disabled, name='payment_system_disabled'),

    # ================================
    # 🚀 Moosyl Integration
    # ================================
    
    # شراء حزمة جديدة
    path('purchase-bundle/', views.purchase_bundle, name='purchase_bundle'),
    
    # Webhook من Moosyl
    path('moosyl/webhook/', views.moosyl_webhook, name='moosyl_webhook'),
    
    # التحقق من حالة حزمة
    path('bundle/<int:bundle_id>/status/', views.check_bundle_status, name='check_bundle_status'),
]