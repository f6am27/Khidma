# complaints/urls.py
from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # ==================== User URLs ====================
    # إنشاء شكوى
    path('submit/', views.UserComplaintCreateView.as_view(), name='submit-complaint'),
    
    # قائمة شكاوى المستخدم
    path('my-complaints/', views.UserComplaintListView.as_view(), name='my-complaints'),
    
    # تفاصيل شكوى واحدة
    path('my-complaints/<int:id>/', views.UserComplaintDetailView.as_view(), name='my-complaint-detail'),
    
    # إحصائيات المستخدم
    path('my-stats/', views.user_complaints_stats, name='my-complaints-stats'),
    
    # ==================== Admin URLs ====================
    # سيتم إضافتها في admin_api/urls.py
]