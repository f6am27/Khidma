#tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ==================== Client Endpoints ====================
    # Task management
    path('create/', views.ServiceRequestCreateView.as_view(), name='create-service-request'),
    path('my-tasks/', views.ClientTasksListView.as_view(), name='my-tasks'),
    path('<int:pk>/', views.ServiceRequestDetailView.as_view(), name='service-request-detail'),
    path('<int:pk>/update/', views.ServiceRequestUpdateView.as_view(), name='task-update'),
    
    # Task candidates management
    path('<int:pk>/candidates/', views.TaskCandidatesListView.as_view(), name='task-candidates'),
    path('<int:pk>/accept/', views.accept_worker, name='accept-worker'),
    
    # ✅ Task status - الآن فقط cancelled
    path('<int:pk>/status/', views.update_task_status, name='update-task-status'),
    
    # Task review
    path('<int:pk>/review/', views.TaskReviewCreateView.as_view(), name='create-task-review'),
    path('my-reviews/', views.WorkerReceivedReviewsView.as_view(), name='worker-reviews'),
    path('review-stats/', views.TaskReviewStatsView.as_view(), name='review-stats'),
    
    # ==================== Worker Endpoints ====================
    # Available tasks
    path('available/', views.AvailableTasksListView.as_view(), name='available-tasks'),
    path('map-data/', views.tasks_map_data, name='tasks-map-data'), 
    path('<int:pk>/apply/', views.TaskApplicationCreateView.as_view(), name='apply-to-task'),
    
    # ==================== Statistics ====================
    path('stats/', views.task_stats, name='task-stats'),
]