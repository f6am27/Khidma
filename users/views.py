# users/views.py - الملف الكامل
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import User, WorkerProfile, ClientProfile
from .utils import to_e164
from .serializers import (
    ChangePasswordSerializer, RegisterSerializer, VerifySerializer, LoginSerializer,
    PasswordResetStartSerializer, PasswordResetConfirmSerializer,
    ResendOTPSerializer, UserSerializer, WorkerProfileUpdateSerializer, 
    ClientProfileUpdateSerializer, WorkerOnboardingSerializer, 
    LocationUpdateSerializer, LocationSharingToggleSerializer, 
    WorkerProfileSerializer, ClientProfileSerializer
)
from .services import (
    start_registration, verify_otp, resend_registration,
    start_password_reset, confirm_password_reset, resend_password_reset
)


# تحديث RegisterView
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
        
        # الحصول على IP address
        ip_address = get_client_ip(request)
        
        # بدء عملية التسجيل وإرسال OTP مع IP
        validated_data = serializer.validated_data
        result = start_registration(
            username=validated_data['username'],
            phone=validated_data['phone'],
            password=validated_data['password'],
            lang=validated_data.get('lang', 'ar'),
            role=validated_data.get('role', 'client'),
            ip_address=ip_address
        )
        
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
        
        # ✅ فحص حالة التعليق
        if user.is_suspended:
            from django.utils import timezone
            
            if user.suspended_until:
                # تعليق مؤقت
                now = timezone.now()
                if now < user.suspended_until:
                    # الحساب لا يزال معلقاً
                    time_remaining = user.suspended_until - now
                    days_remaining = time_remaining.days
                    hours_remaining = time_remaining.seconds // 3600
                    jour_text = "jour" if days_remaining <= 1 else "jours"
                    heure_text = "heure" if hours_remaining <= 1 else "heures"
                    suspension_message = (
                        f"Votre compte est temporairement suspendu jusqu'au {user.suspended_until.strftime('%d/%m/%Y à %H:%M')}.\n"
                        f"Temps restant : {days_remaining} {jour_text} et {hours_remaining} {heure_text}.\n"
                        f"Pour toute question, contactez le support : khidma.helpp@gmail.com"
                    )
                    
                    return Response({
                        "code": "account_suspended",
                        "detail": suspension_message,
                        "suspended_until": user.suspended_until.isoformat(),
                        "days_remaining": days_remaining,
                        "hours_remaining": hours_remaining,
                        "support_email": "khidma.helpp@gmail.com"
                    }, status=status.HTTP_403_FORBIDDEN)
                else:
                    # انتهى وقت التعليق - إعادة التفعيل تلقائياً
                    user.is_suspended = False
                    # user.is_active = True
                    user.suspended_until = None
                    user.suspension_reason = ''
                    user.save(update_fields=['is_suspended', 'suspended_until', 'suspension_reason'])
            else:
                # تعليق نهائي (permanent ban)
                return Response({
                    "code": "account_permanently_suspended",
                    "detail": (
                        "تم إيقاف حسابك نهائياً.\n"
                        "للاستفسار، تواصل مع الدعم الفني: khidma.helpp@gmail.com"
                    ),
                    "support_email": "khidma.helpp@gmail.com"
                }, status=status.HTTP_403_FORBIDDEN)
        
        # ✅ تحديث is_online و is_available عند تسجيل الدخول
        if user.is_worker and hasattr(user, 'worker_profile'):
            user.worker_profile.is_online = True
            user.worker_profile.is_available = True
            user.worker_profile.location_sharing_enabled = True
            user.worker_profile.save(update_fields=['is_online', 'is_available','location_sharing_enabled'])
        
        # ✅ حفظ Device Token
        device_token = request.data.get('device_token')
        device_name = request.data.get('device_name', 'Unknown Device')
        platform = request.data.get('platform', 'unknown')
        
        if device_token:
            from notifications.models import DeviceToken
            DeviceToken.objects.update_or_create(
                user=user,
                token=device_token,
                defaults={
                    'device_name': device_name,
                    'platform': platform,
                    'is_active': True
                }
            )
        
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


# تحديث ResendRegisterOTPView
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
        
        # الحصول على IP address
        ip_address = get_client_ip(request)
        
        # تحديث resend_registration لتدعم IP
        result = resend_registration(
            phone=serializer.validated_data['phone'],
            lang=serializer.validated_data.get('lang', 'ar'),
            ip_address=ip_address
        )
        
        if "error" in result:
            error_code, error_detail = result["error"]
            return Response({
                "code": error_code, 
                "detail": error_detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result["ok"], status=status.HTTP_200_OK)
    

# تحديث ResendPasswordResetOTPView
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
        
        # الحصول على IP address
        ip_address = get_client_ip(request)
        
        # تحديث resend_password_reset لتدعم IP
        result = resend_password_reset(
            phone=serializer.validated_data['phone'],
            lang=serializer.validated_data.get('lang', 'ar'),
            ip_address=ip_address
        )
        
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

class ChangePasswordView(APIView):
    """
    تغيير كلمة المرور
    POST /api/users/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response({
                "code": "validation_error",
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # تغيير كلمة المرور
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            "success": True,
            "message": "تم تغيير كلمة المرور بنجاح"
        }, status=status.HTTP_200_OK)
    
class LogoutView(APIView):
    """
    تسجيل الخروج
    POST /api/users/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # إذا كان عامل، أوقف كل شيء
        if user.is_worker and hasattr(user, 'worker_profile'):
            worker_profile = user.worker_profile
            worker_profile.is_online = False
            worker_profile.is_available = False  # ✅ جديد
            worker_profile.location_sharing_enabled = False
            worker_profile.location_status = 'disabled'
            worker_profile.save(update_fields=[
                'is_online',
                'is_available',  # ✅ جديد
                'location_sharing_enabled', 
                'location_status'
            ])
        
        return Response({
            "success": True,
            "message": "تم تسجيل الخروج بنجاح"
        }, status=status.HTTP_200_OK)   

class SetWorkerOnlineView(APIView):
    """
    تحديث حالة is_online للعامل
    POST /api/users/set-online/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if not user.is_worker:
            return Response({
                "code": "not_worker",
                "detail": "هذا العضو ليس عاملاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not hasattr(user, 'worker_profile'):
            return Response({
                "code": "profile_not_found",
                "detail": "ملف العامل غير موجود"
            }, status=status.HTTP_404_NOT_FOUND)
        
        is_online = request.data.get('is_online', True)
        
        worker_profile = user.worker_profile
        worker_profile.is_online = is_online
        worker_profile.is_available = True  # ✅ جديد - دائماً متاح عند فتح التطبيق
        worker_profile.save(update_fields=['is_online', 'is_available'])
        
        return Response({
            "success": True,
            "message": f"تم تحديث الحالة إلى {'متصل' if is_online else 'غير متصل'}",
            "data": {
                "is_online": worker_profile.is_online,
                "is_available": worker_profile.is_available  # ✅ جديد
            }
        }, status=status.HTTP_200_OK)
    
# ====== Views الجديدة لإدارة الملفات الشخصية ======

class WorkerProfileView(APIView):
    """
    عرض وتحديث ملف العامل
    GET/PUT /api/users/worker-profile/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """عرض ملف العامل"""
        if not request.user.is_worker:
            return Response({
                "code": "not_worker",
                "detail": "هذا العضو ليس عاملاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            worker_profile = request.user.worker_profile
            serializer = WorkerProfileSerializer(worker_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WorkerProfile.DoesNotExist:
            return Response({
                "code": "profile_not_found",
                "detail": "ملف العامل غير موجود"
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request):
        """تحديث ملف العامل"""
        if not request.user.is_worker:
            return Response({
                "code": "not_worker",
                "detail": "هذا العضو ليس عاملاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            worker_profile = request.user.worker_profile
        except WorkerProfile.DoesNotExist:
            return Response({
                "code": "profile_not_found",
                "detail": "ملف العامل غير موجود"
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkerProfileUpdateSerializer(
            worker_profile, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            
            # إرجاع البيانات المحدثة
            response_serializer = WorkerProfileSerializer(worker_profile)
            return Response({
                "success": True,
                "message": "تم تحديث الملف الشخصي بنجاح",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ClientProfileView(APIView):
    """
    عرض وتحديث ملف العميل
    GET/PUT /api/users/client-profile/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """عرض ملف العميل"""
        if not request.user.is_client:
            return Response({
                "code": "not_client",
                "detail": "هذا العضو ليس عميلاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # إنشاء ملف العميل إذا لم يكن موجوداً
        client_profile, created = ClientProfile.objects.get_or_create(
            user=request.user
        )
        
        serializer = ClientProfileSerializer(client_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        """تحديث ملف العميل"""
        if not request.user.is_client:
            return Response({
                "code": "not_client",
                "detail": "هذا العضو ليس عميلاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # إنشاء ملف العميل إذا لم يكن موجوداً
        client_profile, created = ClientProfile.objects.get_or_create(
            user=request.user
        )
        
        serializer = ClientProfileUpdateSerializer(
            client_profile, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            
            # إرجاع البيانات المحدثة
            response_serializer = ClientProfileSerializer(client_profile)
            return Response({
                "success": True,
                "message": "تم تحديث الملف الشخصي بنجاح",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class WorkerOnboardingView(APIView):
    """
    إكمال Onboarding للعامل (إنشاء WorkerProfile)
    POST /api/users/worker-onboarding/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_worker:
            return Response({
                "code": "not_worker",
                "detail": "هذا العضو ليس عاملاً"
            }, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.onboarding_completed:
            return Response({
                "code": "already_completed",
                "detail": "تم إكمال البيانات مسبقاً"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if hasattr(request.user, 'worker_profile'):
            return Response({
                "code": "profile_exists",
                "detail": "ملف العامل موجود مسبقاً"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = WorkerOnboardingSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                worker_profile = serializer.save()
            
            response_serializer = WorkerProfileSerializer(worker_profile)
            return Response({
                "success": True,
                "message": "تم إكمال بيانات العامل بنجاح",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_worker_location(request):
    """
    تحديث موقع العامل الحالي
    POST /api/users/update-location/
    """
    if not request.user.is_worker:
        return Response({
            "code": "not_worker",
            "detail": "هذا العضو ليس عاملاً"
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        return Response({
            "code": "profile_not_found",
            "detail": "ملف العامل غير موجود"
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LocationUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تحديث الموقع
    success = worker_profile.update_current_location(
        latitude=serializer.validated_data['latitude'],
        longitude=serializer.validated_data['longitude'],
        accuracy=serializer.validated_data.get('accuracy')
    )
    
    if not success:
        return Response({
            "code": "location_sharing_disabled",
            "detail": "مشاركة الموقع معطلة"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        "success": True,
        "message": "تم تحديث الموقع بنجاح",
        "data": {
            "latitude": float(worker_profile.current_latitude),
            "longitude": float(worker_profile.current_longitude),
            "location_status": worker_profile.location_status,
            "last_updated": worker_profile.location_last_updated.isoformat()
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_location_sharing(request):
    """
    تفعيل/إلغاء مشاركة الموقع
    POST /api/users/toggle-location-sharing/
    """
    if not request.user.is_worker:
        return Response({
            "code": "not_worker",
            "detail": "هذا العضو ليس عاملاً"
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        return Response({
            "code": "profile_not_found",
            "detail": "ملف العامل غير موجود"
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LocationSharingToggleSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "code": "validation_error",
            "detail": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تغيير حالة المشاركة
    new_status = worker_profile.toggle_location_sharing(
        enabled=serializer.validated_data['enabled']
    )
    
    return Response({
        "success": True,
        "message": f"تم {'تفعيل' if new_status else 'إلغاء'} مشاركة الموقع",
        "data": {
            "location_sharing_enabled": new_status,
            "location_status": worker_profile.location_status,
            "updated_at": worker_profile.location_sharing_updated_at.isoformat() if worker_profile.location_sharing_updated_at else None
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_worker_location_info(request):
    """
    الحصول على معلومات الموقع للعامل
    GET /api/users/location-info/
    """
    if not request.user.is_worker:
        return Response({
            "code": "not_worker",
            "detail": "هذا العضو ليس عاملاً"
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        return Response({
            "code": "profile_not_found",
            "detail": "ملف العامل غير موجود"
        }, status=status.HTTP_404_NOT_FOUND)
    
    # تحديث حالة الموقع قبل الإرجاع
    worker_profile.update_location_status()
    
    return Response({
        "success": True,
        "data": {
            "location_sharing_enabled": worker_profile.location_sharing_enabled,
            "location_status": worker_profile.location_status,
            "current_latitude": float(worker_profile.current_latitude) if worker_profile.current_latitude else None,
            "current_longitude": float(worker_profile.current_longitude) if worker_profile.current_longitude else None,
            "location_accuracy": worker_profile.location_accuracy,
            "last_updated": worker_profile.location_last_updated.isoformat() if worker_profile.location_last_updated else None,
            "is_location_fresh": worker_profile.is_location_fresh(),
            "is_available_with_location": worker_profile.is_currently_available_with_location
        }
    }, status=status.HTTP_200_OK)

# في users/views.py - أضف helper function للحصول على IP

def get_client_ip(request):
    """الحصول على عنوان IP الحقيقي للعميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip