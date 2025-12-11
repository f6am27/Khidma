# complaints/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from .models import Complaint
from .serializers import (
    ComplaintListSerializer,
    ComplaintDetailSerializer,
    ComplaintCreateSerializer,
    ComplaintUpdateSerializer,
    UserComplaintSerializer
)

# ==================== User Views (Client/Worker) ====================

class UserComplaintCreateView(generics.CreateAPIView):
    """
    إنشاء شكوى جديدة (للمستخدمين)
    POST /api/complaints/submit/
    """
    serializer_class = ComplaintCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        complaint = serializer.save()
        
        # إرسال إشعار للأدمن (سيتم تطبيقه لاحقاً)
        # send_admin_notification(complaint)
        
        response_serializer = UserComplaintSerializer(complaint, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'تم إرسال الشكوى بنجاح',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class UserComplaintListView(generics.ListAPIView):
    """
    قائمة شكاوى المستخدم الخاصة
    GET /api/complaints/my-complaints/
    """
    serializer_class = UserComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """إرجاع شكاوى المستخدم الحالي فقط"""
        user = self.request.user
        queryset = Complaint.objects.filter(user=user)
        
        # فلترة حسب الحالة
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class UserComplaintDetailView(generics.RetrieveAPIView):
    """
    تفاصيل شكوى واحدة (للمستخدم صاحب الشكوى فقط)
    GET /api/complaints/my-complaints/<id>/
    """
    serializer_class = UserComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        """المستخدم يمكنه رؤية شكاواه فقط"""
        return Complaint.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_complaints_stats(request):
    """
    إحصائيات شكاوى المستخدم
    GET /api/complaints/my-stats/
    """
    user = request.user
    
    total_complaints = Complaint.objects.filter(user=user).count()
    new_complaints = Complaint.objects.filter(user=user, status='new').count()
    resolved_complaints = Complaint.objects.filter(user=user, status='resolved').count()
    pending_complaints = Complaint.objects.filter(
        user=user, 
        status__in=['new', 'under_review']
    ).count()
    
    return Response({
        'success': True,
        'data': {
            'total_complaints': total_complaints,
            'new_complaints': new_complaints,
            'resolved_complaints': resolved_complaints,
            'pending_complaints': pending_complaints
        }
    }, status=status.HTTP_200_OK)


# ==================== Admin Views ====================

class AdminComplaintListView(generics.ListAPIView):
    """
    قائمة جميع الشكاوى (للأدمن فقط)
    GET /api/admin/complaints/
    """
    serializer_class = ComplaintListSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = Complaint.objects.all().select_related('user', 'resolved_by')
        
        # فلترة حسب الحالة
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # فلترة حسب الفئة
        category_filter = self.request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        # فلترة حسب نوع المستخدم
        user_role = self.request.query_params.get('user_role')
        if user_role:
            queryset = queryset.filter(user__role=user_role)
        
        # فلترة حسب الأولوية
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # البحث
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search) |
                Q(description__icontains=search) |
                Q(admin_notes__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class AdminComplaintDetailView(generics.RetrieveUpdateAPIView):
    """
    تفاصيل وتحديث شكوى (للأدمن فقط)
    GET/PUT /api/admin/complaints/<id>/
    """
    queryset = Complaint.objects.all().select_related('user', 'resolved_by')
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ComplaintDetailSerializer
        return ComplaintUpdateSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ComplaintDetailSerializer(instance, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_complaint = serializer.save()
        
        # إرسال إشعار للمستخدم بالتحديث (سيتم تطبيقه لاحقاً)
        # send_user_notification(updated_complaint)
        
        response_serializer = ComplaintDetailSerializer(
            updated_complaint, 
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'message': 'تم تحديث الشكوى بنجاح',
            'data': response_serializer.data
        }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def admin_delete_complaint(request, complaint_id):
    """
    حذف شكوى (للأدمن فقط)
    DELETE /api/admin/complaints/<id>/delete/
    """
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    complaint_info = {
        'id': complaint.id,
        'user': complaint.user.get_full_name() or complaint.user.phone,
        'category': complaint.get_category_display()
    }
    
    complaint.delete()
    
    return Response({
        'success': True,
        'message': 'تم حذف الشكوى بنجاح',
        'deleted_complaint': complaint_info
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_complaints_stats(request):
    """
    إحصائيات الشكاوى للأدمن
    GET /api/admin/complaints/stats/
    """
    # إحصائيات عامة
    total_complaints = Complaint.objects.count()
    new_complaints = Complaint.objects.filter(status='new').count()
    under_review = Complaint.objects.filter(status='under_review').count()
    resolved_complaints = Complaint.objects.filter(status='resolved').count()
    closed_complaints = Complaint.objects.filter(status='closed').count()
    
    # إحصائيات حسب الأولوية
    urgent_complaints = Complaint.objects.filter(priority='urgent').count()
    important_complaints = Complaint.objects.filter(priority='important').count()
    
    # إحصائيات حسب نوع المستخدم
    client_complaints = Complaint.objects.filter(user__role='client').count()
    worker_complaints = Complaint.objects.filter(user__role='worker').count()
    
    # إحصائيات حسب الفئة
    complaints_by_category = Complaint.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # إحصائيات حسب النوع
    text_complaints = Complaint.objects.filter(type='text').count()
    audio_complaints = Complaint.objects.filter(type='audio').count()
    both_complaints = Complaint.objects.filter(type='both').count()
    
    # الشكاوى الأخيرة (آخر 30 يوم)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_complaints = Complaint.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    
    # متوسط وقت الاستجابة (للشكاوى المحلولة)
    resolved = Complaint.objects.filter(
        status__in=['resolved', 'closed'],
        resolved_at__isnull=False
    )
    
    avg_response_time_seconds = 0
    if resolved.exists():
        total_seconds = sum([
            (c.resolved_at - c.created_at).total_seconds() 
            for c in resolved
        ])
        avg_response_time_seconds = total_seconds / resolved.count()
    
    avg_response_hours = round(avg_response_time_seconds / 3600, 1)
    
    return Response({
        'success': True,
        'data': {
            'overview': {
                'total_complaints': total_complaints,
                'new_complaints': new_complaints,
                'under_review': under_review,
                'resolved_complaints': resolved_complaints,
                'closed_complaints': closed_complaints,
                'recent_complaints_30days': recent_complaints
            },
            'by_priority': {
                'urgent': urgent_complaints,
                'important': important_complaints,
                'normal': total_complaints - urgent_complaints - important_complaints
            },
            'by_user_role': {
                'clients': client_complaints,
                'workers': worker_complaints
            },
            'by_type': {
                'text': text_complaints,
                'audio': audio_complaints,
                'both': both_complaints
            },
            'by_category': list(complaints_by_category),
            'performance': {
                'average_response_time_hours': avg_response_hours
            }
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_bulk_update_status(request):
    """
    تحديث حالة عدة شكاوى دفعة واحدة
    POST /api/admin/complaints/bulk-update/
    Body: {
        "complaint_ids": [1, 2, 3],
        "status": "resolved",
        "admin_notes": "ملاحظات اختيارية"
    }
    """
    complaint_ids = request.data.get('complaint_ids', [])
    new_status = request.data.get('status')
    admin_notes = request.data.get('admin_notes', '')
    
    if not complaint_ids or not new_status:
        return Response({
            'success': False,
            'error': 'complaint_ids و status مطلوبان'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if new_status not in ['new', 'under_review', 'resolved', 'closed']:
        return Response({
            'success': False,
            'error': 'حالة غير صحيحة'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    complaints = Complaint.objects.filter(id__in=complaint_ids)
    
    if not complaints.exists():
        return Response({
            'success': False,
            'error': 'لم يتم العثور على شكاوى'
        }, status=status.HTTP_404_NOT_FOUND)
    
    updated_count = 0
    for complaint in complaints:
        complaint.status = new_status
        if admin_notes:
            complaint.admin_notes = admin_notes
        
        if new_status in ['resolved', 'closed']:
            complaint.resolved_by = request.user
            complaint.resolved_at = timezone.now()
        
        complaint.save()
        updated_count += 1
    
    return Response({
        'success': True,
        'message': f'تم تحديث {updated_count} شكوى بنجاح',
        'updated_count': updated_count
    }, status=status.HTTP_200_OK)