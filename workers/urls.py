# workers/urls.py
from django.urls import path
from .views import (
    WorkerListView,
    WorkerDetailView,
    WorkerServiceListView,
    WorkerProfileCreateView,
    WorkerProfileUpdateView,
    worker_search_filters,
    worker_stats
)

urlpatterns = [
    # Worker listing and search (for clients)
    path('', WorkerListView.as_view(), name='worker-list'),
    
    # ✅ إضافة المسارات المفقودة
    path('search/filters/', worker_search_filters, name='worker-search-filters'),
    path('stats/', worker_stats, name='worker-stats'),
    
    # Worker details
    path('<int:id>/', WorkerDetailView.as_view(), name='worker-detail'),
    path('<int:worker_id>/services/', WorkerServiceListView.as_view(), name='worker-services'),
    
    # Worker profile management (for workers themselves)
    path('profile/create/', WorkerProfileCreateView.as_view(), name='worker-profile-create'),
    path('profile/update/', WorkerProfileUpdateView.as_view(), name='worker-profile-update'),
]