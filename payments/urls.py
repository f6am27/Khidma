# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # List and create payments
    path('', views.PaymentListCreateView.as_view(), name='payment-list-create'),
    
    # Get specific payment details
    path('<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    
    # Get my payments (made or received)
    path('my-payments/', views.MyPaymentsView.as_view(), name='my-payments'),
    
    # Get payments received (workers only)
    path('received/', views.ReceivedPaymentsView.as_view(), name='received-payments'),
    
    # Get payment statistics
    path('statistics/', views.payment_statistics, name='statistics'),
    
    # Get payment history with filters
    path('history/', views.payment_history, name='history'),
]