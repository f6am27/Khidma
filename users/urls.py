# users/urls.py
from django.urls import path
from .views import (
    RegisterView, VerifyView, LoginView,
    PasswordResetStartView, PasswordResetConfirmView,
    ResendRegisterOTPView, ResendPasswordResetOTPView,
    CompleteOnboardingView, UserProfileView
)

urlpatterns = [
    # المصادقة الأساسية
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    
    # استعادة كلمة المرور
    path('password/reset/', PasswordResetStartView.as_view(), name='password_reset'),
    path('password/confirm/', PasswordResetConfirmView.as_view(), name='password_confirm'),
    
    # إعادة إرسال OTP
    path('resend/', ResendRegisterOTPView.as_view(), name='resend_register'),
    path('password/resend/', ResendPasswordResetOTPView.as_view(), name='resend_password'),
    
    # إكمال البيانات
    path('onboarding/complete/', CompleteOnboardingView.as_view(), name='complete_onboarding'),
    
    # ملف المستخدم
    path('profile/', UserProfileView.as_view(), name='user_profile'),
]