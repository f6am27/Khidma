# clients/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Client Profile
    path('profile/', views.ClientProfileView.as_view(), name='client-profile'),
    path('stats/', views.ClientStatsView.as_view(), name='client-stats'),
    path('dashboard/', views.client_dashboard_data, name='client-dashboard'),
    
    # Favorite Workers
    path('favorites/', views.FavoriteWorkersListView.as_view(), name='favorite-workers-list'),
    path('favorites/add/', views.FavoriteWorkerCreateView.as_view(), name='favorite-worker-create'),
    path('favorites/<int:worker_id>/remove/', views.FavoriteWorkerDeleteView.as_view(), name='favorite-worker-delete'),
    path('favorites/<int:worker_id>/toggle/', views.toggle_favorite_worker, name='toggle-favorite-worker'),
    path('favorites/<int:worker_id>/status/', views.check_worker_favorite_status, name='check-favorite-status'),
    
    # Notifications
    path('notifications/', views.ClientNotificationsListView.as_view(), name='client-notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_as_read, name='mark-all-notifications-read'),
    
    # Settings
    path('settings/', views.ClientSettingsView.as_view(), name='client-settings'),
]