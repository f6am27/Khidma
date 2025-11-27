# admin_api/views.py
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from users.models import User, WorkerProfile, ClientProfile,AdminProfile
from tasks.models import ServiceRequest, TaskApplication, TaskReview
from payments.models import Payment
from chat.models import Report, Conversation, Message
from services.models import ServiceCategory, NouakchottArea
from notifications.models import Notification,NotificationSettings
from notifications.serializers import NotificationListSerializer
from .email_service import (
    generate_otp, 
    send_password_reset_email, 
    store_otp, 
    verify_otp, 
    clear_otp
)
from .serializers import (
    DashboardStatsSerializer,
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    UserSuspensionSerializer,
    AdminReportListSerializer,
    ReportActionSerializer,
    AdminCategorySerializer,
    AdminAreaSerializer,
    FinancialSummarySerializer,
    AdminProfileUpdateSerializer,
    AdminProfileSerializer,
    AdminChangePasswordSerializer,
    AdminPasswordResetRequestSerializer,
    AdminPasswordResetConfirmSerializer
)


# ==================== Admin Authentication ====================
class AdminLoginView(APIView):
    """تسجيل دخول الأدمن"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email and password required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            if user.role != 'admin' and not user.is_superuser:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'error': 'Account is disabled'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # ✅ تعيين الأدمن كمتصل
        admin_profile, created = AdminProfile.objects.get_or_create(user=user)
        admin_profile.set_online()
        admin_profile.last_login_dashboard = timezone.now()
        admin_profile.save(update_fields=['last_login_dashboard'])
        
        # Create JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': getattr(user, 'role', 'admin'),
                'is_online': admin_profile.is_online,  # ✅ أضف
            }
        })

# ==================== Dashboard Statistics ====================
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def dashboard_stats(request):
    """إحصائيات Dashboard الرئيسية"""
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # Users Stats
    total_users = User.objects.filter(role__in=['client', 'worker']).count()
    total_clients = User.objects.filter(role='client').count()
    total_workers = User.objects.filter(role='worker').count()
    new_users_this_month = User.objects.filter(
        role__in=['client', 'worker'],
        date_joined__gte=month_start
    ).count()
    
    # Tasks Stats
    total_tasks = ServiceRequest.objects.count()
    active_tasks = ServiceRequest.objects.filter(status='active').count()
    completed_tasks = ServiceRequest.objects.filter(status='completed').count()
    cancelled_tasks = ServiceRequest.objects.filter(status='cancelled').count()
    
    # Financial Stats
    total_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_this_month = Payment.objects.filter(
        status='completed',
        completed_at__gte=month_start
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    average_task_value = Payment.objects.filter(
        status='completed'
    ).aggregate(Avg('amount'))['amount__avg'] or 0
    
    # Reports Stats
    pending_reports = Report.objects.filter(status='pending').count()
    resolved_reports = Report.objects.filter(status='resolved').count()
    
    # Growth Rates
    last_month_users = User.objects.filter(
        role__in=['client', 'worker'],
        date_joined__gte=last_month_start,
        date_joined__lt=month_start
    ).count()
    
    user_growth_rate = 0
    if last_month_users > 0:
        user_growth_rate = ((new_users_this_month - last_month_users) / last_month_users) * 100
    
    task_completion_rate = 0
    if total_tasks > 0:
        task_completion_rate = (completed_tasks / total_tasks) * 100
    
    data = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_workers': total_workers,
        'new_users_this_month': new_users_this_month,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'cancelled_tasks': cancelled_tasks,
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'average_task_value': average_task_value,
        'pending_reports': pending_reports,
        'resolved_reports': resolved_reports,
        'user_growth_rate': round(user_growth_rate, 2),
        'task_completion_rate': round(task_completion_rate, 2)
    }
    
    serializer = DashboardStatsSerializer(data)
    return Response(serializer.data)


# ==================== Users Management ====================
class AdminUserListView(generics.ListAPIView):
    """قائمة المستخدمين"""
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = User.objects.filter(role__in=['client', 'worker'])
        
        # Filters
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        status_filter = self.request.query_params.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, is_suspended=False)
        elif status_filter == 'suspended':
            queryset = queryset.filter(is_suspended=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset.order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveDestroyAPIView):  # ✅ غيرنا من RetrieveAPIView
    """تفاصيل المستخدم + الحذف"""
    serializer_class = AdminUserDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.filter(role__in=['client', 'worker'])
    lookup_field = 'id'
    
    def destroy(self, request, *args, **kwargs):
        """حذف المستخدم"""
        instance = self.get_object()
        user_id = instance.id
        user_name = instance.get_full_name() or instance.phone
        
        # حذف المستخدم
        self.perform_destroy(instance)
        
        return Response({
            'success': True,
            'message': 'تم حذف المستخدم بنجاح',
            'user_id': user_id,
            'user_name': user_name
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def suspend_user(request, user_id):
    """تعليق مستخدم"""
    user = get_object_or_404(User, id=user_id, role__in=['client', 'worker'])
    
    serializer = UserSuspensionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    days = serializer.validated_data.get('days')
    reason = serializer.validated_data.get('reason', '')
    permanent = serializer.validated_data.get('permanent', False)
    
    user.is_suspended = True
    
    if permanent:
        user.suspended_until = None
        user.suspension_reason = reason or 'حظر نهائي من الإدارة'
    elif days:
        user.suspended_until = timezone.now() + timedelta(days=days)
        user.suspension_reason = reason or f'تعليق {days} يوم من الإدارة'
    
    # ✅ التعديل الأول: إضافة update_fields
    user.save(update_fields=['is_suspended', 'suspension_reason', 'suspended_until'])
    
    return Response({
        'message': 'تم تعليق المستخدم بنجاح',
        'user_id': user_id,
        'suspended_until': user.suspended_until,
        'reason': user.suspension_reason
    })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def unsuspend_user(request, user_id):
    """إلغاء تعليق مستخدم"""
    user = get_object_or_404(User, id=user_id, role__in=['client', 'worker'])
    
    user.is_suspended = False
    user.suspended_until = None
    user.suspension_reason = ''
    
    # ✅ التعديل الثاني: إضافة update_fields
    user.save(update_fields=['is_suspended', 'suspension_reason', 'suspended_until'])
    
    return Response({
        'message': 'تم إلغاء تعليق المستخدم بنجاح',
        'user_id': user_id
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def delete_user(request, user_id):
    """حذف مستخدم"""
    user = get_object_or_404(User, id=user_id, role__in=['client', 'worker'])
    user.delete()
    
    return Response({
        'message': 'تم حذف المستخدم بنجاح',
        'user_id': user_id
    })


# ==================== Reports Management ====================
class AdminReportListView(generics.ListAPIView):
    """قائمة البلاغات"""
    serializer_class = AdminReportListSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = Report.objects.all()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('reporter', 'reported_user').order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def handle_report(request, report_id):
    """معالجة بلاغ"""
    report = get_object_or_404(Report, id=report_id)
    
    serializer = ReportActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    action = serializer.validated_data['action']
    admin_notes = serializer.validated_data.get('admin_notes', '')
    
    if action == 'resolve':
        report.status = 'resolved'
        report.resolved_at = timezone.now()
        report.resolved_by = request.user
        report.admin_notes = admin_notes
        report.save()
        
        return Response({'message': 'تم حل البلاغ بنجاح'})
    
    elif action == 'dismiss':
        report.status = 'dismissed'
        report.resolved_at = timezone.now()
        report.resolved_by = request.user
        report.admin_notes = admin_notes
        report.save()
        
        return Response({'message': 'تم رفض البلاغ'})
    
    elif action in ['suspend_3days', 'suspend_7days', 'suspend_30days', 'permanent_ban']:
        user = report.reported_user
        user.is_suspended = True
        
        if action == 'suspend_3days':
            user.suspended_until = timezone.now() + timedelta(days=3)
            user.suspension_reason = f'تعليق 3 أيام - بلاغ #{report.id}'
            days = 3
        elif action == 'suspend_7days':
            user.suspended_until = timezone.now() + timedelta(days=7)
            user.suspension_reason = f'تعليق 7 أيام - بلاغ #{report.id}'
            days = 7
        elif action == 'suspend_30days':
            user.suspended_until = timezone.now() + timedelta(days=30)
            user.suspension_reason = f'تعليق 30 يوم - بلاغ #{report.id}'
            days = 30
        else:  # permanent_ban
            user.suspended_until = None
            user.suspension_reason = f'حظر نهائي - بلاغ #{report.id}'
            days = 'permanent'
        
        # ✅ التعديل الثالث: إضافة update_fields
        user.save(update_fields=['is_suspended', 'suspension_reason', 'suspended_until'])
        
        report.status = 'resolved'
        report.resolved_at = timezone.now()
        report.resolved_by = request.user
        report.admin_notes = f"تم {'الحظر النهائي' if days == 'permanent' else f'التعليق {days} أيام'}"
        report.save()
        
        return Response({
            'message': f'تم {"الحظر النهائي" if days == "permanent" else f"تعليق المستخدم {days} أيام"}',
            'user_suspended': True
        })


# ==================== Categories Management ====================
class AdminCategoryListView(generics.ListCreateAPIView):
    """إدارة الفئات"""
    queryset = ServiceCategory.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """تفاصيل/تعديل/حذف فئة"""
    queryset = ServiceCategory.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'


# ==================== Areas Management ====================
class AdminAreaListView(generics.ListCreateAPIView):
    """إدارة المناطق"""
    queryset = NouakchottArea.objects.all()
    serializer_class = AdminAreaSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminAreaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """تفاصيل/تعديل/حذف منطقة"""
    queryset = NouakchottArea.objects.all()
    serializer_class = AdminAreaSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'


# ==================== Financial Reports ====================
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def financial_summary(request):
    """ملخص مالي"""
    
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # Total transactions
    total_transactions = Payment.objects.count()
    completed_transactions = Payment.objects.filter(status='completed').count()
    
    # Revenue
    total_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_this_month = Payment.objects.filter(
        status='completed',
        completed_at__gte=month_start
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    revenue_last_month = Payment.objects.filter(
        status='completed',
        completed_at__gte=last_month_start,
        completed_at__lt=month_start
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    average_transaction_value = Payment.objects.filter(
        status='completed'
    ).aggregate(Avg('amount'))['amount__avg'] or 0
    
    # Top earning workers
    top_workers = Payment.objects.filter(
        status='completed'
    ).values('receiver__id', 'receiver__first_name', 'receiver__last_name', 'receiver__phone').annotate(
        total_earned=Sum('amount')
    ).order_by('-total_earned')[:10]
    
    top_earning_workers = [
        {
            'id': worker['receiver__id'],
            'name': f"{worker['receiver__first_name']} {worker['receiver__last_name']}" if worker['receiver__first_name'] else worker['receiver__phone'],
            'total_earned': float(worker['total_earned'])
        }
        for worker in top_workers
    ]
    
    # Revenue by category
    revenue_by_cat = Payment.objects.filter(
        status='completed'
    ).values('task__service_category__name').annotate(
        revenue=Sum('amount')
    ).order_by('-revenue')
    
    revenue_by_category = {
        item['task__service_category__name']: float(item['revenue'])
        for item in revenue_by_cat if item['task__service_category__name']
    }
    
    data = {
        'total_transactions': total_transactions,
        'completed_transactions': completed_transactions,
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'revenue_last_month': revenue_last_month,
        'average_transaction_value': average_transaction_value,
        'top_earning_workers': top_earning_workers,
        'revenue_by_category': revenue_by_category
    }
    
    serializer = FinancialSummarySerializer(data)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_logout(request):
    """
    تسجيل خروج الأدمن
    POST /api/admin/logout/
    """
    user = request.user
    
    if user.role == 'admin' and hasattr(user, 'admin_profile'):
        user.admin_profile.set_offline()
    
    return Response({
        'success': True,
        'message': 'تم تسجيل الخروج بنجاح'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_heartbeat(request):
    """
    Heartbeat للحفاظ على حالة الاتصال
    POST /api/admin/heartbeat/
    """
    user = request.user
    
    if user.role == 'admin':
        admin_profile, created = AdminProfile.objects.get_or_create(user=user)
        
        if not admin_profile.is_online:
            admin_profile.set_online()
        else:
            admin_profile.update_activity()
        
        return Response({
            'success': True,
            'is_online': admin_profile.is_online,
            'last_activity': admin_profile.last_activity.isoformat()
        }, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Not an admin'
    }, status=status.HTTP_403_FORBIDDEN)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_status(request):
    """
    الحصول على حالة الأدمن
    GET /api/admin/status/
    """
    user = request.user
    
    if user.role == 'admin':
        admin_profile, created = AdminProfile.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'data': {
                'is_online': admin_profile.is_online,
                'last_activity': admin_profile.last_activity.isoformat() if admin_profile.last_activity else None,
                'last_login_dashboard': admin_profile.last_login_dashboard.isoformat() if admin_profile.last_login_dashboard else None,
            }
        }, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Not an admin'
    }, status=status.HTTP_403_FORBIDDEN)



@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAdminUser])
def admin_profile(request):
    """
    جلب أو تحديث بيانات الأدمن
    GET /api/admin/profile/
    PUT /api/admin/profile/
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        # جلب البيانات
        serializer = AdminProfileSerializer(user, context={'request': request})
        
        # إضافة بيانات AdminProfile إذا كانت موجودة
        data = serializer.data
        if hasattr(user, 'admin_profile'):
            profile = user.admin_profile
            data['display_name'] = profile.display_name
            data['bio'] = profile.bio
            data['department'] = profile.department
            data['is_online'] = profile.is_online
            data['last_activity'] = profile.last_activity.isoformat() if profile.last_activity else None
        
        return Response({
            'success': True,
            'data': data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # تحديث البيانات
        serializer = AdminProfileUpdateSerializer(
            user, 
            data=request.data, 
            partial=True,  # السماح بتحديث جزئي
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # إرجاع البيانات المحدثة
            response_serializer = AdminProfileSerializer(user, context={'request': request})
            response_data = response_serializer.data
            
            if hasattr(user, 'admin_profile'):
                profile = user.admin_profile
                response_data['display_name'] = profile.display_name
                response_data['bio'] = profile.bio
                response_data['department'] = profile.department
            
            # تحديث localStorage في الفرونت
            return Response({
                'success': True,
                'message': 'Profil mis à jour avec succès',
                'data': response_data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_change_password(request):
    """
    تغيير كلمة مرور الأدمن
    POST /api/admin/change-password/
    
    Body:
    {
        "old_password": "...",
        "new_password": "...",
        "new_password_confirm": "..."
    }
    """
    user = request.user
    
    # التحقق من أن المستخدم أدمن
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = AdminChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تغيير كلمة المرور
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    
    return Response({
        'success': True,
        'message': 'Mot de passe mis à jour avec succès'
    }, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def admin_password_reset_request(request):
    """
    طلب إعادة تعيين كلمة المرور
    POST /api/admin/password-reset-request/
    
    Body: { "email": "...", "language": "fr" }
    """
    serializer = AdminPasswordResetRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    language = serializer.validated_data.get('language', 'fr')
    
    # توليد OTP
    otp = generate_otp()
    
    # حفظ في cache
    store_otp(email, otp)
    
    # إرسال عبر Email
    email_sent = send_password_reset_email(email, otp, language)
    
    if not email_sent:
        return Response({
            'success': False,
            'error': 'Erreur lors de l\'envoi de l\'email'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': True,
        'message': 'Code de vérification envoyé à votre email'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def admin_password_reset_confirm(request):
    """
    تأكيد إعادة التعيين وتغيير كلمة المرور
    POST /api/admin/password-reset-confirm/
    
    Body: {
        "email": "...",
        "otp": "123456",
        "new_password": "...",
        "new_password_confirm": "..."
    }
    """
    serializer = AdminPasswordResetConfirmSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    otp = serializer.validated_data['otp']
    new_password = serializer.validated_data['new_password']
    
    # التحقق من OTP
    valid, message = verify_otp(email, otp)
    
    if not valid:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تحديث كلمة المرور
    try:
        user = User.objects.get(email=email, role='admin')
        user.set_password(new_password)
        user.save()
        
        # حذف OTP
        clear_otp(email)
        
        return Response({
            'success': True,
            'message': 'Mot de passe réinitialisé avec succès'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Utilisateur introuvable'
        }, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_notifications(request):
    """
    قائمة إشعارات الأدمن
    GET /api/admin/notifications/
    Query params:
    - is_read: true/false
    - limit: عدد النتائج (افتراضي 20)
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # الحصول على الإشعارات
    notifications = Notification.objects.filter(
        recipient=user
    ).order_by('-created_at')
    
    # فلترة حسب حالة القراءة
    is_read = request.query_params.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
    # الحد من النتائج
    limit = int(request.query_params.get('limit', 20))
    notifications = notifications[:limit]
    
    serializer = NotificationListSerializer(notifications, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'total': notifications.count()
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_notifications_unread_count(request):
    """
    عدد الإشعارات غير المقروءة
    GET /api/admin/notifications/unread-count/
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    unread_count = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()
    
    return Response({
        'success': True,
        'unread_count': unread_count
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAdminUser])
def admin_mark_notification_read(request, notification_id):
    """
    تحديد إشعار كمقروء
    PUT /api/admin/notifications/:id/read/
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=user
        )
        notification.mark_as_read()
        
        return Response({
            'success': True,
            'message': 'Notification marquée comme lue'
        }, status=status.HTTP_200_OK)
        
    except Notification.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Notification non trouvée'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([permissions.IsAdminUser])
def admin_mark_all_read(request):
    """
    تحديد جميع الإشعارات كمقروءة
    PUT /api/admin/notifications/mark-all-read/
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    from django.utils import timezone
    updated_count = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'success': True,
        'message': f'{updated_count} notifications marquées comme lues',
        'updated_count': updated_count
    }, status=status.HTTP_200_OK)


class AdminNotificationSettingsView(generics.RetrieveUpdateAPIView):
    """
    إعدادات الإشعارات للأدمن
    Admin notification settings
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        """الحصول على إعدادات الإشعارات أو إنشاؤها"""
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user,
            defaults={'notifications_enabled': True}
        )
        return settings
    
    def get_serializer_class(self):
        from notifications.serializers import NotificationSettingsSerializer
        return NotificationSettingsSerializer