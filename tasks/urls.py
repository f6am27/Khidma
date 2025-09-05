# tasks/urls.py
from django.urls import path
from .views import (
    # Client views (task management)
    ServiceRequestCreateView,
    ClientTasksListView,
    ServiceRequestDetailView,
    ServiceRequestUpdateView,
    TaskCandidatesListView,
    accept_worker,
    update_task_status,
    TaskReviewCreateView,
    
    # Worker views (available tasks)
    AvailableTasksListView,
    TaskApplicationCreateView,
    
    # Statistics
    task_stats,
)

urlpatterns = [
    # Client endpoints - Task management (matching Flutter screens)
    path('', ServiceRequestCreateView.as_view(), name='task-create'),  # POST - Create task
    path('my/', ClientTasksListView.as_view(), name='my-tasks'),  # GET - My tasks (with ?status filter)
    path('<int:pk>/', ServiceRequestDetailView.as_view(), name='task-detail'),  # GET - Task details
    path('<int:pk>/update/', ServiceRequestUpdateView.as_view(), name='task-update'),  # PUT - Update task
    
    # Task candidates management (matching TaskCandidatesScreen)
    path('<int:pk>/candidates/', TaskCandidatesListView.as_view(), name='task-candidates'),  # GET - View candidates
    path('<int:pk>/accept-worker/', accept_worker, name='accept-worker'),  # POST - Accept worker
    
    # Task status management (matching Flutter task flow)
    path('<int:pk>/status/', update_task_status, name='update-task-status'),  # PUT - Update status
    
    # Task review (matching completed task evaluation)
    path('<int:pk>/review/', TaskReviewCreateView.as_view(), name='task-review'),  # POST - Review task
    
    # Worker endpoints - Available tasks (for worker app screens)
    path('available/', AvailableTasksListView.as_view(), name='available-tasks'),  # GET - Available tasks for workers
    path('<int:pk>/apply/', TaskApplicationCreateView.as_view(), name='apply-task'),  # POST - Apply for task
    
    # Statistics
    path('stats/', task_stats, name='task-stats'),  # GET - Task statistics
]