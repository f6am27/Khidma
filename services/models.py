# services/models.py
from django.db import models

class ServiceCategory(models.Model):
    """
    Service categories (e.g., Cleaning, Plumbing, etc.)
    فئات الخدمات
    """
    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100)  # Arabic name
    icon = models.CharField(max_length=50)  # Icon name for Flutter
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)  # Display order
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class NouakchottArea(models.Model):
    """
    Nouakchott districts and neighborhoods
    مناطق نواكشوط
    """
    AREA_TYPE_CHOICES = [
        ('district', 'District'),      # مقاطعة
        ('neighborhood', 'Neighborhood'),  # حي
    ]

    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100)
    area_type = models.CharField(max_length=20, choices=AREA_TYPE_CHOICES, default='district')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_areas')
    
    # GPS coordinates (optional for now)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['area_type', 'order', 'name']
        verbose_name_plural = "Nouakchott Areas"

    def __str__(self):
        return f"{self.name} ({self.get_area_type_display()})"