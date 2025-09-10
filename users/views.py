# users/views.py
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .utils import to_e164
from .serializers import (
    RegisterSerializer, VerifySerializer, LoginSerializer,
    PasswordResetStartSerializer, PasswordResetConfirmSerializer,
    ResendOTPSerializer, UserSerializer
)
from .services import (
    start_registration, verify_otp, resend_registration,
    start_password_reset, confirm_password_reset, resend_password_reset
)


class RegisterView(APIView):
    """
    تسجيل مستخدم جديد
    POST /api/users/register
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # بدء عملية التسجيل وإرسال OTP
        result = start_registration(**serializer.validated_data)
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "status": "otp_sent", 
            **result["ok"]
        }, status=status.HTTP_201_CREATED)


class VerifyView(APIView):
    """
    التحقق من رمز OTP وإنشاء الحساب
    POST /api/users/verify
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # التحقق من OTP وإنشاء المستخدم
        result = verify_otp(**serializer.validated_data)
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)

        # الحصول على المستخدم المُنشأ حديثاً
        try:
            phone_e164 = to_e164(serializer.validated_data["phone"])
            user = User.objects.get(phone=phone_e164)
        except User.DoesNotExist:
            return Response({
                "code": "user_not_found", 
                "detail": "المستخدم غير موجود بعد التحقق"
            }, status=status.HTTP_400_BAD_REQUEST)

        # إنشاء JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "status": "verified",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.first_name,
                "role": user.role,
                "onboarding_completed": user.onboarding_completed,
            }
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    تسجيل الدخول
    POST /api/users/login
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # المستخدم تم التحقق منه في serializer
        user = serializer.validated_data['user']
        
        # إنشاء JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.first_name,
                "role": user.role,
                "onboarding_completed": user.onboarding_completed,
            }
        }, status=status.HTTP_200_OK)


class PasswordResetStartView(APIView):
    """
    بدء عملية استعادة كلمة المرور
    POST /api/users/password/reset
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = start_password_reset(**serializer.validated_data)
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result["ok"], status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    تأكيد استعادة كلمة المرور
    POST /api/users/password/confirm
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = confirm_password_reset(
            phone=serializer.validated_data["phone"],
            code=serializer.validated_data["code"],
            new_password=serializer.validated_data["new_password"]
        )
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result["ok"], status=status.HTTP_200_OK)


class ResendRegisterOTPView(APIView):
    """
    إعادة إرسال رمز التسجيل
    POST /api/users/resend
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = resend_registration(**serializer.validated_data)
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result["ok"], status=status.HTTP_200_OK)


class ResendPasswordResetOTPView(APIView):
    """
    إعادة إرسال رمز استعادة كلمة المرور
    POST /api/users/password/resend
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "invalid_input", 
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = resend_password_reset(**serializer.validated_data)
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result["ok"], status=status.HTTP_200_OK)


class CompleteOnboardingView(APIView):
    """
    إكمال onboarding للعامل
    POST /api/users/onboarding/complete
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if not user.is_worker:
            return Response({
                "code": "not_worker", 
                "detail": "only_workers_can_complete"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.onboarding_completed:
            user.onboarding_completed = True
            user.save(update_fields=["onboarding_completed", "updated_at"])

        return Response({
            "status": "ok",
            "user": {
                "id": user.id,
                "username": user.first_name,
                "role": user.role,
                "onboarding_completed": True,
            }
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """
    عرض وتحديث بيانات المستخدم
    GET/PUT /api/users/profile
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """عرض بيانات المستخدم الحالي"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        """تحديث بيانات المستخدم الأساسية"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response({
            "code": "invalid_input", 
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)