# services/serializers.py
from rest_framework import serializers
from .models import ServiceCategory, NouakchottArea

class ServiceCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for service categories
    محول بيانات فئات الخدمات
    """
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 
            'name', 
            'name_ar', 
            'icon', 
            'description', 
            'description_ar', 
            'is_active',
            'order'
        ]
        read_only_fields = ['id']


class NouakchottAreaSerializer(serializers.ModelSerializer):
    """
    Serializer for Nouakchott areas
    محول بيانات مناطق نواكشوط
    """
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = NouakchottArea
        fields = [
            'id', 
            'name', 
            'name_ar', 
            'area_type', 
            'parent', 
            'parent_name',
            'latitude', 
            'longitude', 
            'is_active',
            'order'
        ]
        read_only_fields = ['id', 'parent_name']


class NouakchottAreaSimpleSerializer(serializers.ModelSerializer):
    """
    Simple serializer for areas (for dropdowns)
    محول بسيط للمناطق (للقوائم المنسدلة)
    """
    class Meta:
        model = NouakchottArea
        fields = ['id', 'name', 'name_ar']