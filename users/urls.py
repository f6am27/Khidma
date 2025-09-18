# users/urls.py
from django.urls import path
from .views import (
    RegisterView, VerifyView, LoginView,
    PasswordResetStartView, PasswordResetConfirmView,
    ResendRegisterOTPView, ResendPasswordResetOTPView,
    CompleteOnboardingView, UserProfileView
)
from .upload_views import (
    upload_profile_image,
    delete_profile_image,
    get_profile_image,
    get_image_upload_info
)

app_name = 'users'

urlpatterns = [
    # ====== مصادقة المستخدم الأساسية ======
    path('register/', RegisterView.as_view(), name='register'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),

    # ====== استعادة كلمة المرور ======
    path('password/reset/', PasswordResetStartView.as_view(), name='password_reset'),
    path('password/confirm/', PasswordResetConfirmView.as_view(), name='password_confirm'),

    # ====== إعادة إرسال OTP ======
    path('resend/', ResendRegisterOTPView.as_view(), name='resend_register'),
    path('password/resend/', ResendPasswordResetOTPView.as_view(), name='resend_password'),

    # ====== إكمال بيانات المستخدم ======
    path('onboarding/complete/', CompleteOnboardingView.as_view(), name='complete_onboarding'),

    # ====== ملف المستخدم ======
    path('profile/', UserProfileView.as_view(), name='user_profile'),

    # ====== مسارات إدارة الصور ======
    path('upload-profile-image/', upload_profile_image, name='upload_profile_image'),
    path('delete-profile-image/', delete_profile_image, name='delete_profile_image'),
    path('profile-image/', get_profile_image, name='get_profile_image'),
    path('image-upload-info/', get_image_upload_info, name='get_image_upload_info'),
]
