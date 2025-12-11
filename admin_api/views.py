# admin_api/views.py
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.db.models import Count, Sum, Avg, Q, Max
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from users.models import User, WorkerProfile, ClientProfile,AdminProfile
from tasks.models import ServiceRequest, TaskApplication, TaskReview
from chat.models import Report, Conversation, Message
from services.models import ServiceCategory, NouakchottArea
from notifications.models import Notification,NotificationSettings
from notifications.serializers import NotificationListSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from complaints.models import Complaint
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
from workers.models import WorkerService 
from payments.models import UserTaskCounter  
 

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
                'is_online': admin_profile.is_online,
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
    
    # ❌ Financial Stats - معطل مؤقتاً
    total_revenue = 0
    revenue_this_month = 0
    average_task_value = 0
    
    # Reports Stats
    pending_reports = Report.objects.filter(status='pending').count()
    resolved_reports = Report.objects.filter(status='resolved').count()
    total_complaints = Complaint.objects.count()
    new_complaints_count = Complaint.objects.filter(status='new').count()
    pending_complaints_count = Complaint.objects.filter(
        status__in=['new', 'under_review']
    ).count()
    
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
        'task_completion_rate': round(task_completion_rate, 2),
        'total_complaints': total_complaints,
        'new_complaints': new_complaints_count,
        'pending_complaints': pending_complaints_count
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


class AdminUserDetailView(generics.RetrieveDestroyAPIView):
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
    """❌ ملخص مالي - معطل مؤقتاً"""
    return Response({
        'message': 'نظام التقارير المالية معطل مؤقتاً',
        'note': 'سيتم تفعيله مع نظام الاشتراك الشهري'
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


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
        serializer = AdminProfileSerializer(user, context={'request': request})
        
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
        serializer = AdminProfileUpdateSerializer(
            user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            response_serializer = AdminProfileSerializer(user, context={'request': request})
            response_data = response_serializer.data
            
            if hasattr(user, 'admin_profile'):
                profile = user.admin_profile
                response_data['display_name'] = profile.display_name
                response_data['bio'] = profile.bio
                response_data['department'] = profile.department
            
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
    """
    user = request.user
    
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
    """
    serializer = AdminPasswordResetRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    language = serializer.validated_data.get('language', 'fr')
    
    otp = generate_otp()
    store_otp(email, otp)
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
    
    valid, message = verify_otp(email, otp)
    
    if not valid:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email, role='admin')
        user.set_password(new_password)
        user.save()
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
    """
    user = request.user
    
    if user.role != 'admin':
        return Response({
            'success': False,
            'error': 'Non autorisé'
        }, status=status.HTTP_403_FORBIDDEN)
    
    notifications = Notification.objects.filter(
        recipient=user
    ).order_by('-created_at')
    
    is_read = request.query_params.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
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
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user,
            defaults={'notifications_enabled': True}
        )
        return settings
    
    def get_serializer_class(self):
        from notifications.serializers import NotificationSettingsSerializer
        return NotificationSettingsSerializer
    
# ================================
# 📊 STATISTICS & ANALYTICS APIs
# ================================

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def top_rated_users(request):
    """
    ✅ 1. المستخدمون الأكثر تقييماً (للمكافأة)
    GET /api/admin/analytics/top-rated/
    Query params:
    - limit: عدد النتائج (default: 10)
    - min_reviews: حد أدنى للتقييمات (default: 5)
    """
    from .serializers import TopRatedUserSerializer
    
    # Filters
    limit = int(request.query_params.get('limit', 10))
    min_reviews = int(request.query_params.get('min_reviews', 2))
    
    # جلب العمال مع التقييمات
    workers = User.objects.filter(
        role='worker',
        worker_profile__isnull=False
    ).select_related('worker_profile').annotate(
        avg_rating=Avg('received_reviews__rating'),
        review_count=Count('received_reviews')
    ).filter(
        review_count__gte=min_reviews,
        avg_rating__isnull=False
    ).order_by('-avg_rating', '-review_count')[:limit]
    
    # تحضير البيانات
    data = []
    for worker in workers:
        profile = worker.worker_profile
        
        # رابط الصورة
        profile_image_url = None
        if profile and profile.profile_image:
            profile_image_url = request.build_absolute_uri(profile.profile_image.url)
        
        data.append({
            'user_id': worker.id,
            'user_name': worker.get_full_name() or worker.phone,
            'phone': worker.phone,
            'role': worker.role,
            'average_rating': float(worker.avg_rating or 0),
            'total_reviews': worker.review_count,
            'total_jobs_completed': profile.total_jobs_completed if profile else 0,
            'date_joined': worker.date_joined,
            'profile_image_url': profile_image_url
        })
    
    serializer = TopRatedUserSerializer(data, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'count': len(data),
        'filters': {
            'limit': limit,
            'min_reviews': min_reviews
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def most_reported_users(request):
    """
    ✅ 2. المستخدمون الأكثر بلاغات
    GET /api/admin/analytics/most-reported/
    Query params:
    - limit: عدد النتائج (default: 20)
    - status: pending/resolved/dismissed
    - role: worker/client
    """
    from .serializers import MostReportedUserSerializer
    
    # Filters
    limit = int(request.query_params.get('limit', 20))
    status_filter = request.query_params.get('status')
    role_filter = request.query_params.get('role')
    
    # إحصاء البلاغات لكل مستخدم
    reports_query = Report.objects.values('reported_user').annotate(
        total_reports=Count('id'),
        pending_reports=Count('id', filter=Q(status='pending')),
        resolved_reports=Count('id', filter=Q(status='resolved')),
        dismissed_reports=Count('id', filter=Q(status='dismissed')),
        last_report=Max('created_at')
    ).order_by('-total_reports')
    
    # فلترة حسب الحالة
    if status_filter:
        reports_query = reports_query.filter(
            **{f'{status_filter}_reports__gt': 0}
        )
    
    # جلب المستخدمين
    user_ids = [r['reported_user'] for r in reports_query[:limit]]
    users = User.objects.filter(id__in=user_ids)
    
    # فلترة حسب النوع
    if role_filter:
        users = users.filter(role=role_filter)
    
    # تحضير البيانات
    reports_dict = {r['reported_user']: r for r in reports_query}
    
    data = []
    for user in users:
        report_data = reports_dict.get(user.id, {})
        
        data.append({
            'user_id': user.id,
            'user_name': user.get_full_name() or user.phone,
            'phone': user.phone,
            'role': user.role,
            'total_reports': report_data.get('total_reports', 0),
            'pending_reports': report_data.get('pending_reports', 0),
            'resolved_reports': report_data.get('resolved_reports', 0),
            'dismissed_reports': report_data.get('dismissed_reports', 0),
            'last_report_date': report_data.get('last_report'),
            'is_suspended': user.is_suspended,
            'suspension_reason': user.suspension_reason or None
        })
    
    # ترتيب حسب العدد الكلي
    data.sort(key=lambda x: x['total_reports'], reverse=True)
    
    serializer = MostReportedUserSerializer(data, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'count': len(data),
        'filters': {
            'limit': limit,
            'status': status_filter,
            'role': role_filter
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def subscription_analytics(request):
    """
    إحصائيات الاشتراكات والمستخدمين Premium/Free
    GET /api/admin/analytics/subscriptions/
    """
    if not request.user.is_staff and not request.user.role == 'admin':
        return Response({
            'success': False,
            'error': 'Unauthorized - Admin access only'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from payments.models import UserTaskCounter
        
        # ✅ إحصائيات المستخدمين
        total_users = User.objects.filter(role__in=['client', 'worker']).count()
        
        # ✅ حساب Premium vs Free من UserTaskCounter
        premium_users = UserTaskCounter.objects.filter(is_premium=True).count()
        free_users = UserTaskCounter.objects.filter(is_premium=False).count()
        
        # ✅ المستخدمين عند 4 مهام (على وشك الوصول للحد)
        users_at_4_tasks = UserTaskCounter.objects.filter(
            accepted_tasks_count=4,
            is_premium=False
        ).count()
        
        # ✅ المستخدمين عند 5 مهام (وصلوا للحد المجاني)
        users_at_5_tasks = UserTaskCounter.objects.filter(
            accepted_tasks_count__gte=5,
            is_premium=False
        ).count()
        
        # ✅ معدل التحويل (Conversion Rate)
        conversion_rate = 0.0
        if total_users > 0:
            conversion_rate = round((premium_users / total_users) * 100, 2)
        
        # ✅ الإيرادات المحتملة شهرياً (8 MRU × عدد Premium)
        monthly_revenue_potential = premium_users * 8
        
        # ✅ تفصيل Premium vs Free حسب الدور
        premium_clients = UserTaskCounter.objects.filter(
            is_premium=True,
            user__role='client'
        ).count()
        
        premium_workers = UserTaskCounter.objects.filter(
            is_premium=True,
            user__role='worker'
        ).count()
        
        free_clients = UserTaskCounter.objects.filter(
            is_premium=False,
            user__role='client'
        ).count()
        
        free_workers = UserTaskCounter.objects.filter(
            is_premium=False,
            user__role='worker'
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'total_users': total_users,
                'premium_users': premium_users,
                'free_users': free_users,
                'users_at_4_tasks': users_at_4_tasks,
                'users_at_5_tasks': users_at_5_tasks,
                'conversion_rate': conversion_rate,
                'monthly_revenue_potential': monthly_revenue_potential,
                'breakdown': {
                    'premium_clients': premium_clients,
                    'premium_workers': premium_workers,
                    'free_clients': free_clients,
                    'free_workers': free_workers
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def platform_activity(request):
    """
    ✅ 4. نشاط المنصة
    GET /api/admin/analytics/activity/
    """
    from .serializers import PlatformActivitySerializer
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # المهام المنشورة
    tasks_today = ServiceRequest.objects.filter(created_at__gte=today_start).count()
    tasks_week = ServiceRequest.objects.filter(created_at__gte=week_start).count()
    tasks_month = ServiceRequest.objects.filter(created_at__gte=month_start).count()
    
    # المهام المقبولة (active)
    accepted_today = ServiceRequest.objects.filter(
        status='active',
        updated_at__gte=today_start
    ).count()
    accepted_week = ServiceRequest.objects.filter(
        status='active',
        updated_at__gte=week_start
    ).count()
    accepted_month = ServiceRequest.objects.filter(
        status='active',
        updated_at__gte=month_start
    ).count()
    
    # معدل القبول
    acceptance_rate = 0
    if tasks_month > 0:
        acceptance_rate = (accepted_month / tasks_month) * 100
    
    # المهام الملغاة
    cancelled_today = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=today_start
    ).count()
    cancelled_week = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=week_start
    ).count()
    cancelled_month = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=month_start
    ).count()
    
    # معدل الإلغاء
    cancellation_rate = 0
    if tasks_month > 0:
        cancellation_rate = (cancelled_month / tasks_month) * 100
    
    # العمال النشطين
    workers_online = User.objects.filter(
        role='worker',
        worker_profile__is_online=True
    ).count()
    
    workers_with_location = User.objects.filter(
        role='worker',
        worker_profile__location_sharing_enabled=True,
        worker_profile__current_latitude__isnull=False,
        worker_profile__current_longitude__isnull=False
    ).count()
    
    data = {
        'tasks_published_today': tasks_today,
        'tasks_published_this_week': tasks_week,
        'tasks_published_this_month': tasks_month,
        'tasks_accepted_today': accepted_today,
        'tasks_accepted_this_week': accepted_week,
        'tasks_accepted_this_month': accepted_month,
        'acceptance_rate': round(acceptance_rate, 2),
        'tasks_cancelled_today': cancelled_today,
        'tasks_cancelled_this_week': cancelled_week,
        'tasks_cancelled_this_month': cancelled_month,
        'cancellation_rate': round(cancellation_rate, 2),
        'workers_online_now': workers_online,
        'workers_with_active_location': workers_with_location
    }
    
    serializer = PlatformActivitySerializer(data)
    
    return Response({
        'success': True,
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def top_service_categories(request):
    """
    أكثر فئات الخدمات طلباً
    GET /api/admin/analytics/top-categories/?limit=10
    """
    if not request.user.is_staff and not request.user.role == 'admin':
        return Response({
            'success': False,
            'error': 'Unauthorized - Admin access only'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        limit = int(request.GET.get('limit', 10))
        
        categories = ServiceCategory.objects.all()
        
        categories_data = []
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        for category in categories:
            # ✅ إجمالي المهام
            total_tasks = ServiceRequest.objects.filter(
                service_category=category
            ).count()
            
            # ✅ المهام هذا الشهر
            tasks_this_month = ServiceRequest.objects.filter(
                service_category=category,
                created_at__gte=month_start
            ).count()
            
            # ✅ عدد العمال من WorkerProfile (لأن WorkerService فارغ)
            total_workers = User.objects.filter(
                role='worker',
                worker_profile__service_category=category.name
            ).count()
            
            categories_data.append({
                'category_id': category.id,
                'category_name': category.name,  
                'total_tasks': total_tasks,
                'tasks_this_month': tasks_this_month,
                'total_workers': total_workers
            })
        
        # ✅ ترتيب حسب إجمالي المهام
        categories_data.sort(key=lambda x: x['total_tasks'], reverse=True)
        categories_data = categories_data[:limit]
        
        return Response({
            'success': True,
            'data': categories_data,
            'count': len(categories_data),
            'filters': {
                'limit': limit
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"Error in top_service_categories: {str(e)}")
        print(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def most_active_users(request):
    """
    ✅ 6. المستخدمون الأكثر نشاطاً
    GET /api/admin/analytics/most-active/
    Query params:
    - limit: عدد النتائج (default: 20)
    - role: client/worker
    """
    from .serializers import MostActiveUserSerializer
    
    limit = int(request.query_params.get('limit', 20))
    role_filter = request.query_params.get('role')
    
    data = []
    
    if not role_filter or role_filter == 'client':
        # العملاء الأكثر نشاطاً
        # ✅ استخدام service_requests بدلاً من posted_tasks
        clients = User.objects.filter(role='client').annotate(
            tasks_count=Count('service_requests'),  # ✅ الاسم الصحيح
            accepted_count=Count('service_requests', filter=Q(service_requests__status='active'))
        ).filter(tasks_count__gt=0).order_by('-tasks_count')[:limit]
        
        for client in clients:
            data.append({
                'user_id': client.id,
                'user_name': client.get_full_name() or client.phone,
                'phone': client.phone,
                'role': 'client',
                'tasks_published': client.tasks_count,
                'tasks_accepted': client.accepted_count,
                'applications_sent': None,
                'tasks_completed': None,
                'last_activity': client.last_login or client.date_joined,
                'is_online': False
            })
    
    if not role_filter or role_filter == 'worker':
        # العمال الأكثر نشاطاً
        workers = User.objects.filter(role='worker').annotate(
            apps_count=Count('task_applications'),
            completed_count=Count('assigned_tasks', filter=Q(assigned_tasks__status='completed'))
        ).filter(apps_count__gt=0).order_by('-apps_count')[:limit]
        
        for worker in workers:
            is_online = False
            if hasattr(worker, 'worker_profile'):
                is_online = worker.worker_profile.is_online
            
            data.append({
                'user_id': worker.id,
                'user_name': worker.get_full_name() or worker.phone,
                'phone': worker.phone,
                'role': 'worker',
                'tasks_published': None,
                'tasks_accepted': None,
                'applications_sent': worker.apps_count,
                'tasks_completed': worker.completed_count,
                'last_activity': worker.last_login or worker.date_joined,
                'is_online': is_online
            })
    
    # ترتيب حسب النشاط
    if role_filter == 'client':
        data.sort(key=lambda x: x['tasks_published'], reverse=True)
    elif role_filter == 'worker':
        data.sort(key=lambda x: x['applications_sent'], reverse=True)
    else:
        # ترتيب مختلط
        data.sort(key=lambda x: (
            x['tasks_published'] or 0) + (x['applications_sent'] or 0
        ), reverse=True)
    
    data = data[:limit]
    
    serializer = MostActiveUserSerializer(data, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'count': len(data),
        'filters': {
            'limit': limit,
            'role': role_filter
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def cancellation_analytics(request):
    """
    ✅ 7. تحليل الإلغاءات
    GET /api/admin/analytics/cancellations/
    """
    from .serializers import CancellationAnalyticsSerializer
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # إجمالي المهام
    total_tasks = ServiceRequest.objects.count()
    
    # المهام الملغاة
    cancelled_tasks = ServiceRequest.objects.filter(status='cancelled').count()
    
    # معدل الإلغاء
    cancellation_rate = 0
    if total_tasks > 0:
        cancellation_rate = (cancelled_tasks / total_tasks) * 100
    
    # العملاء الأكثر إلغاءً
    # ✅ استخدام service_requests بدلاً من posted_tasks
    top_cancellers_query = User.objects.filter(role='client').annotate(
        cancelled_count=Count('service_requests', filter=Q(service_requests__status='cancelled'))
    ).filter(cancelled_count__gt=0).order_by('-cancelled_count')[:10]
    
    top_cancellers = []
    for client in top_cancellers_query:
        top_cancellers.append({
            'user_id': client.id,
            'user_name': client.get_full_name() or client.phone,
            'phone': client.phone,
            'cancelled_count': client.cancelled_count
        })
    
    # الإلغاءات حسب الوقت
    cancelled_today = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=today_start
    ).count()
    
    cancelled_week = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=week_start
    ).count()
    
    cancelled_month = ServiceRequest.objects.filter(
        status='cancelled',
        updated_at__gte=month_start
    ).count()
    
    data = {
        'total_tasks': total_tasks,
        'cancelled_tasks': cancelled_tasks,
        'cancellation_rate': round(cancellation_rate, 2),
        'top_cancellers': top_cancellers,
        'cancelled_today': cancelled_today,
        'cancelled_this_week': cancelled_week,
        'cancelled_this_month': cancelled_month
    }
    
    serializer = CancellationAnalyticsSerializer(data)
    
    return Response({
        'success': True,
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_growth_chart(request):
    """
    Get monthly user growth from September 2025 to current month
    Returns count of new users registered each month
    """
    try:
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        from datetime import datetime
        
        # Get users grouped by month from September 2025
        users_by_month = User.objects.filter(
            created_at__gte=datetime(2025, 9, 1)  # من سبتمبر 2025
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Format data for frontend
        months_fr = {
            1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 
            5: 'Mai', 6: 'Juin', 7: 'Juil', 8: 'Août',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'
        }
        
        growth_data = []
        cumulative = 0
        
        for entry in users_by_month:
            month_num = entry['month'].month
            cumulative += entry['count']
            growth_data.append({
                'month': months_fr[month_num],
                'new_users': entry['count'],
                'total_users': cumulative,
                'date': entry['month'].strftime('%Y-%m')
            })
        
        return Response({
            'success': True,
            'data': growth_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_tasks(request):
    """
    Get all tasks with optional filters
    """
    try:
        from tasks.models import ServiceRequest
        from django.db.models import Q
        
        # ✅ صحيح
        tasks = ServiceRequest.objects.select_related(
            'client', 'service_category', 'assigned_worker'
        ).all()
        
        # Apply filters
        status = request.GET.get('status')
        category = request.GET.get('category')
        search = request.GET.get('search')
        
        if status:
            tasks = tasks.filter(status=status)
        
        if category:
            tasks = tasks.filter(service_category_id=category)
        
        if search:
            tasks = tasks.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        tasks_data = []
        for task in tasks.order_by('-created_at'):
            # Handle applications count safely
            try:
                applications_count = task.applications.count()
            except:
                applications_count = 0
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'budget': task.budget,
                'location': task.location,
                'client_name': task.client.get_full_name() if task.client else 'N/A',
                'client_phone': task.client.phone if task.client else 'N/A',
                'category_name': task.service_category.name if task.service_category else None,
                'category_icon': task.service_category.icon if task.service_category else None,
                'created_at': task.created_at.isoformat(),
                'applications_count': applications_count,
                'accepted_worker_name': task.assigned_worker.get_full_name() if task.assigned_worker else None,
            })
        
        return Response({
            'success': True,
            'data': tasks_data,
            'total': len(tasks_data)
        })
        
    except Exception as e:
        import traceback
        print("Error in get_all_tasks:", str(e))
        print(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_tasks_stats(request):
    """
    Get task statistics
    """
    try:
        from tasks.models import ServiceRequest
        
        total_tasks = ServiceRequest.objects.count()
        published_tasks = ServiceRequest.objects.filter(status='published').count()
        active_tasks = ServiceRequest.objects.filter(status='active').count()
        cancelled_tasks = ServiceRequest.objects.filter(status='cancelled').count()
        
        return Response({
            'success': True,
            'data': {
                'total_tasks': total_tasks,
                'published_tasks': published_tasks,
                'active_tasks': active_tasks,
                'cancelled_tasks': cancelled_tasks
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_categories(request):
    """
    Get all service categories
    """
    try:
        from services.models import ServiceCategory  # ← غيري من tasks إلى services
        
        categories = ServiceCategory.objects.all().order_by('name')
        
        categories_data = []
        for cat in categories:
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'icon': cat.icon,
                'description': cat.description
            })
        
        return Response({
            'success': True,
            'data': categories_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def users_at_limit(request):
    """
    Get users close to or at the free task limit (4 or 5+ tasks)
    GET /api/admin/users/at-limit/
    """
    try:
        from payments.models import UserTaskCounter
        
        # ✅ جلب المستخدمين عند 4 مهام أو 5+ مهام
        users = UserTaskCounter.objects.filter(
            accepted_tasks_count__gte=4,  # 4 أو أكثر
            is_premium=False  # فقط المستخدمين المجانيين
        ).select_related('user').order_by('-accepted_tasks_count')
        
        users_data = []
        for counter in users:
            user = counter.user
            users_data.append({
                'user_id': user.id,
                'user_name': user.get_full_name() or user.phone,
                'phone': user.phone,
                'role': user.role,
                'tasks_count': counter.accepted_tasks_count,
                'is_premium': counter.is_premium,
                'date_joined': user.date_joined.isoformat()
            })
        
        return Response({
            'success': True,
            'data': users_data,
            'count': len(users_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# admin_api/views.py
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def daily_tasks_chart(request):
    """
    عدد المهام المنشورة يومياً آخر 7 أيام
    """
    from datetime import timedelta
    
    today = timezone.now().date()
    data = []
    days_fr = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    for i in range(6, -1, -1):  
        day = today - timedelta(days=i)
        count = ServiceRequest.objects.filter(
            created_at__date=day
        ).count()
        
        data.append({
            'day': days_fr[day.weekday()],
            'tasks': count,
            'date': day.isoformat()
        })
    
    return Response({'success': True, 'data': data})

