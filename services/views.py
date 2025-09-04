# services/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import ServiceCategory, NouakchottArea
from .serializers import (
    ServiceCategorySerializer, 
    NouakchottAreaSerializer,
    NouakchottAreaSimpleSerializer
)

class ServiceCategoryListView(generics.ListAPIView):
    """
    List all active service categories
    عرض جميع فئات الخدمات النشطة
    """
    queryset = ServiceCategory.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'name_ar']
    ordering_fields = ['order', 'name']
    ordering = ['order']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by language preference إذا أراد المستخدم لغة معينة
        lang = self.request.query_params.get('lang', None)
        if lang:
            # يمكن إضافة منطق للغة لاحقاً
            pass
            
        return queryset


class NouakchottAreaListView(generics.ListAPIView):
    """
    List all active Nouakchott areas
    عرض جميع مناطق نواكشوط النشطة
    """
    queryset = NouakchottArea.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = NouakchottAreaSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'name_ar']
    filterset_fields = ['area_type', 'parent']
    ordering_fields = ['order', 'name']
    ordering = ['order']


class NouakchottAreaSimpleListView(generics.ListAPIView):
    """
    Simple list of areas (for dropdowns in Flutter)
    قائمة بسيطة للمناطق (للقوائم المنسدلة في Flutter)
    """
    queryset = NouakchottArea.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = NouakchottAreaSimpleSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by area type if specified
        area_type = self.request.query_params.get('type', None)
        if area_type:
            queryset = queryset.filter(area_type=area_type)
            
        return queryset


class ServiceCategoryDetailView(generics.RetrieveAPIView):
    """
    Get details of a specific service category
    الحصول على تفاصيل فئة خدمة معينة
    """
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


class NouakchottAreaDetailView(generics.RetrieveAPIView):
    """
    Get details of a specific area
    الحصول على تفاصيل منطقة معينة
    """
    queryset = NouakchottArea.objects.filter(is_active=True)
    serializer_class = NouakchottAreaSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


# إضافية: API للحصول على الكل في طلب واحد (لتحسين الأداء)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def services_data_combined(request):
    """
    Get all services data in one request (categories + areas)
    الحصول على جميع بيانات الخدمات في طلب واحد (فئات + مناطق)
    """
    categories = ServiceCategory.objects.filter(is_active=True).order_by('order', 'name')
    areas = NouakchottArea.objects.filter(is_active=True).order_by('order', 'name')
    
    return Response({
        'categories': ServiceCategorySerializer(categories, many=True).data,
        'areas': NouakchottAreaSimpleSerializer(areas, many=True).data
    }, status=status.HTTP_200_OK)