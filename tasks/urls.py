# tasks/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Client endpoints - Task management
    path('create/', views.ServiceRequestCreateView.as_view(), name='create-service-request'),  # POST - Create task
    path('my-tasks/', views.ClientTasksListView.as_view(), name='my-tasks'),
    path('<int:pk>/', views.ServiceRequestDetailView.as_view(), name='service-request-detail'),  # GET - Task details
    path('<int:pk>/update/', views.ServiceRequestUpdateView.as_view(), name='task-update'),  # PUT - Update task
    
    # Task candidates management
    path('<int:pk>/candidates/', views.TaskCandidatesListView.as_view(), name='task-candidates'),  # GET - View candidates
    path('<int:pk>/accept/', views.accept_worker, name='accept-worker'),  # POST - Accept worker
    
    # Task status management
    path('<int:pk>/status/', views.update_task_status, name='update-task-status'),  # PUT - Update status
    
    # Task review
    path('<int:pk>/review/', views.TaskReviewCreateView.as_view(), name='create-task-review'),  # POST - Review task
    
    # Worker endpoints - Available tasks
    path('available/', views.AvailableTasksListView.as_view(), name='available-tasks'),  # GET - Available tasks for workers
    path('map-data/', views.tasks_map_data, name='tasks-map-data'), 
    path('<int:pk>/apply/', views.TaskApplicationCreateView.as_view(), name='apply-to-task'),  # POST - Apply for task

    
    # Statistics
    path('stats/', views.task_stats, name='task-stats'),  # GET - Task statistics
]
