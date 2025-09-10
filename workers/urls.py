# workers/urls.py - النسخة النهائية الكاملة
from django.urls import path
from .views import (
    WorkerListView,
    WorkerDetailView,
    WorkerProfileView,
    WorkerProfileUpdateView,
    WorkerServiceListView,
    WorkerSettingsView,
    worker_search_filters,
    worker_stats
)

urlpatterns = [
    # Worker listing and search (for clients)
    path('', WorkerListView.as_view(), name='worker-list'),
    
    # Worker search filters and stats
    path('search/filters/', worker_search_filters, name='worker-search-filters'),
    path('stats/', worker_stats, name='worker-stats'),
    
    # Worker details (for clients)
    path('<int:id>/', WorkerDetailView.as_view(), name='worker-detail'),
    path('<int:worker_id>/services/', WorkerServiceListView.as_view(), name='worker-services'),
    
    # Worker profile management (for workers themselves)
    path('profile/', WorkerProfileView.as_view(), name='worker-profile'),
    path('profile/update/', WorkerProfileUpdateView.as_view(), name='worker-profile-update'),
    
    # Worker settings
    path('settings/', WorkerSettingsView.as_view(), name='worker-settings'),
]