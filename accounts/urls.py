from django.urls import path
from .views import RegisterView, VerifyView, LoginView,PasswordResetStartView, PasswordResetConfirmView,ResendRegisterOTPView, ResendPasswordResetOTPView,CompleteOnboardingView
urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    path('verify',   VerifyView.as_view(),   name='verify'),
    path('login',    LoginView.as_view(),    name='login'),
    path('pwd/reset',   PasswordResetStartView.as_view(),   name='pwd_reset'),
    path('pwd/confirm', PasswordResetConfirmView.as_view(), name='pwd_confirm'),
    path('resend',        ResendRegisterOTPView.as_view(),      name='resend_register'),
    path('pwd/resend',    ResendPasswordResetOTPView.as_view(), name='resend_pwd'),
    path('onboarding/complete', CompleteOnboardingView.as_view()),  # ADD

]
