# workers/urls.py - النسخة النهائية بعد إضافة URLs المواقع الجديدة

from django.urls import path
from .views import (
    WorkerListView,
    WorkerDetailView,
    WorkerProfileView,
    WorkerProfileUpdateView,
    WorkerServiceListView,
    WorkerSettingsView,
    worker_search_filters,
    worker_stats,
    toggle_location_sharing,
    update_current_location,
    get_location_status,
    get_nearby_tasks,
    get_nearby_workers
)

urlpatterns = [
    # ==================== APIs الموقع الجديدة ====================
    path('location/toggle/', toggle_location_sharing, name='toggle-location-sharing'),
    path('location/update/', update_current_location, name='update-current-location'),
    path('location/status/', get_location_status, name='get-location-status'),
    path('tasks/nearby/', get_nearby_tasks, name='get-nearby-tasks'),
    path('nearby/', get_nearby_workers, name='get-nearby-workers'),

    # ==================== URLs الأصلية ====================
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
