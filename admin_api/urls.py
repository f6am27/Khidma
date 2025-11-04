# admin_api/urls.py
from django.urls import path
from . import views

app_name = 'admin_api'

urlpatterns = [
    # Authentication
    path('login/', views.AdminLoginView.as_view(), name='admin-login'),
    
    # Dashboard
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    
    # Users Management
    path('users/', views.AdminUserListView.as_view(), name='users-list'),
    path('users/<int:id>/', views.AdminUserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/suspend/', views.suspend_user, name='suspend-user'),
    path('users/<int:user_id>/unsuspend/', views.unsuspend_user, name='unsuspend-user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete-user'),
    
    # Reports Management
    path('reports/', views.AdminReportListView.as_view(), name='reports-list'),
    path('reports/<int:report_id>/handle/', views.handle_report, name='handle-report'),
    
    # Categories Management
    path('categories/', views.AdminCategoryListView.as_view(), name='categories-list'),
    path('categories/<int:id>/', views.AdminCategoryDetailView.as_view(), name='category-detail'),
    
    # Areas Management
    path('areas/', views.AdminAreaListView.as_view(), name='areas-list'),
    path('areas/<int:id>/', views.AdminAreaDetailView.as_view(), name='area-detail'),
    
    # Financial Reports
    path('financial/summary/', views.financial_summary, name='financial-summary'),
]