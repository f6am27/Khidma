from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import normalize_phone, to_e164
from .models import Profile

from .serializers import (
    RegisterSerializer, VerifySerializer, LoginSerializer,
    PasswordResetStartSerializer, PasswordResetConfirmSerializer,
    ResendSerializer
)
from .services import (
    start_registration, verify_otp, resend_registration,
    start_password_reset, confirm_password_reset, resend_password_reset
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = RegisterSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)
        res = start_registration(**s.validated_data)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)
        return Response({"status": "otp_sent", **res["ok"]}, status=201)


class VerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = VerifySerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)

        res = verify_otp(**s.validated_data)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)

        # ✅ عند نجاح التحقق: إصدار JWT + إعادة بيانات المستخدم (role, onboarding)
        try:
            phone_e164 = to_e164(s.validated_data["phone"])
            user = User.objects.get(profile__phone=phone_e164)
        except Exception:
            return Response(
                {"code": "user_not_found", "detail": "المستخدم غير موجود بعد التحقق"},
                status=400
            )

        refresh = RefreshToken.for_user(user)
        prof = getattr(user, "profile", None)

        return Response({
            "status": "verified",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": getattr(prof, "role", "client"),
                "onboarding_completed": bool(getattr(prof, "onboarding_completed", False)),
            }
        }, status=200)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = LoginSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code":"invalid_input","detail":s.errors}, status=400)

        ident = s.validated_data["phone_or_username"].strip()
        password = s.validated_data["password"]

        # نحاول تفسير الإدخال كهاتف؛ إن فشل، نعامله كاسم مستخدم
        username = None
        try:
            phone_e164 = to_e164(ident)   # سيُنجح فقط لو كان ident رقم هاتف صالح
            try:
                user = User.objects.get(profile__phone=phone_e164)
                username = user.username
            except User.DoesNotExist:
                return Response({"code":"user_not_found","detail":"المستخدم غير موجود"}, status=400)
        except Exception:
            # ليس هاتفًا صالحًا → اسم مستخدم
            username = ident

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"code":"invalid_credentials","detail":"بيانات الدخول غير صحيحة"}, status=400)

        refresh = RefreshToken.for_user(user)
        prof = getattr(user, "profile", None)  # ✅ جلب البروفايل

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": getattr(prof, "role", "client"),
                "onboarding_completed": bool(getattr(prof, "onboarding_completed", False)),
            }
        }, status=200)


class PasswordResetStartView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = PasswordResetStartSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)
        res = start_password_reset(**s.validated_data)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)
        return Response(res["ok"], status=200)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)
        payload = {
            "phone": s.validated_data["phone"],
            "code": s.validated_data["code"],
            "new_password": s.validated_data["new_password"],
        }
        res = confirm_password_reset(**payload)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)
        return Response(res["ok"], status=200)


class ResendRegisterOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = ResendSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)
        res = resend_registration(**s.validated_data)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)
        return Response(res["ok"], status=200)


class ResendPasswordResetOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        s = ResendSerializer(data=request.data)
        if not s.is_valid():
            return Response({"code": "invalid_input", "detail": s.errors}, status=400)
        res = resend_password_reset(**s.validated_data)
        if "error" in res:
            code, detail = res["error"]
            return Response({"code": code, "detail": detail}, status=400)
        return Response(res["ok"], status=200)


class CompleteOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prof = getattr(request.user, "profile", None)
        if not prof:
            return Response({"code": "profile_missing", "detail": "profile_missing"}, status=400)

        if prof.role != "worker":
            return Response({"code": "not_worker", "detail": "only_workers_can_complete"}, status=400)

        if not prof.onboarding_completed:
            prof.onboarding_completed = True
            prof.save(update_fields=["onboarding_completed", "updated_at"])

        return Response({
            "status": "ok",
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "role": prof.role,
                "onboarding_completed": True,
            }
        }, status=200)
