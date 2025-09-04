# services/urls.py
from django.urls import path
from .views import (
    ServiceCategoryListView,
    ServiceCategoryDetailView,
    NouakchottAreaListView,
    NouakchottAreaSimpleListView,
    NouakchottAreaDetailView,
    services_data_combined
)

urlpatterns = [
    # Service Categories - فئات الخدمات
    path('categories/', ServiceCategoryListView.as_view(), name='service-categories'),
    path('categories/<int:id>/', ServiceCategoryDetailView.as_view(), name='service-category-detail'),
    
    # Nouakchott Areas - مناطق نواكشوط
    path('areas/', NouakchottAreaListView.as_view(), name='nouakchott-areas'),
    path('areas/simple/', NouakchottAreaSimpleListView.as_view(), name='nouakchott-areas-simple'),
    path('areas/<int:id>/', NouakchottAreaDetailView.as_view(), name='nouakchott-area-detail'),
    
    # Combined data - بيانات مجمعة
    path('all-data/', services_data_combined, name='services-all-data'),
]