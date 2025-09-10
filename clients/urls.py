# clients/urls.py - النسخة النهائية الكاملة
from django.urls import path
from . import views

urlpatterns = [
    # Client Profile Management
    path('profile/', views.ClientProfileView.as_view(), name='client-profile'),
    
    # Client Statistics
    path('stats/', views.client_stats, name='client-stats'),
    
    # Favorite Workers Management
    path('favorites/', views.FavoriteWorkersListView.as_view(), name='favorite-workers-list'),
    path('favorites/add/', views.FavoriteWorkerCreateView.as_view(), name='favorite-worker-create'),
    path('favorites/<int:worker_id>/remove/', views.FavoriteWorkerDeleteView.as_view(), name='favorite-worker-delete'),
    path('favorites/<int:worker_id>/toggle/', views.toggle_favorite_worker, name='toggle-favorite-worker'),
    path('favorites/<int:worker_id>/status/', views.check_worker_favorite_status, name='check-favorite-status'),
    
    # Client Settings
    path('settings/', views.ClientSettingsView.as_view(), name='client-settings'),
    
    # Dashboard
    path('dashboard/', views.client_dashboard_data, name='client-dashboard'),
]