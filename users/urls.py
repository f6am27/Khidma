# users/urls.py - الملف الكامل
from django.urls import path
from .views import (
    RegisterView, VerifyView, LoginView,
    PasswordResetStartView, PasswordResetConfirmView,
    ResendRegisterOTPView, ResendPasswordResetOTPView,
    CompleteOnboardingView, UserProfileView,
    WorkerProfileView, ClientProfileView, WorkerOnboardingView,
    update_worker_location, toggle_location_sharing, get_worker_location_info,ChangePasswordView,LogoutView

)
from .upload_views import (
    upload_profile_image,
    delete_profile_image,
    get_profile_image,
    get_image_upload_info
)
from rest_framework_simplejwt.views import TokenRefreshView


app_name = 'users'

urlpatterns = [
    # ====== مصادقة المستخدم الأساسية ======
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    # ====== استعادة كلمة المرور ======
    path('password/reset/', PasswordResetStartView.as_view(), name='password_reset'),
    path('password/confirm/', PasswordResetConfirmView.as_view(), name='password_confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # ====== إعادة إرسال OTP ======
    path('resend/', ResendRegisterOTPView.as_view(), name='resend_register'),
    path('password/resend/', ResendPasswordResetOTPView.as_view(), name='resend_password'),

    # ====== إكمال بيانات المستخدم ======
    path('onboarding/complete/', CompleteOnboardingView.as_view(), name='complete_onboarding'),
    path('worker-onboarding/', WorkerOnboardingView.as_view(), name='worker_onboarding'),

    # ====== ملف المستخدم الأساسي ======
    path('profile/', UserProfileView.as_view(), name='user_profile'),

    # ====== ملفات التفصيلية للمستخدمين ======
    path('worker-profile/', WorkerProfileView.as_view(), name='worker_profile'),
    path('client-profile/', ClientProfileView.as_view(), name='client_profile'),

    # ====== مسارات إدارة الصور ======
    path('upload-profile-image/', upload_profile_image, name='upload_profile_image'),
    path('delete-profile-image/', delete_profile_image, name='delete_profile_image'),
    path('profile-image/', get_profile_image, name='get_profile_image'),
    path('image-upload-info/', get_image_upload_info, name='get_image_upload_info'),

    # ====== مسارات إدارة المواقع (للعمال فقط) ======
    path('update-location/', update_worker_location, name='update_worker_location'),
    path('toggle-location-sharing/', toggle_location_sharing, name='toggle_location_sharing'),
    path('location-info/', get_worker_location_info, name='get_worker_location_info'),
]