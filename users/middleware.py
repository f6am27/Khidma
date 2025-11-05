from django.utils import timezone
from users.models import User
from datetime import timedelta
from notifications.utils import trigger_payment_check_if_needed

class ReactivateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_check = None
    
    def __call__(self, request):
        now = timezone.now()
        
        # تحقق كل ساعة
        if not self.last_check or (now - self.last_check) > timedelta(hours=1):
            User.objects.filter(
                is_suspended=True,
                suspended_until__lte=now,
                suspended_until__isnull=False
            ).update(
                is_active=True,
                is_suspended=False,
                suspended_until=None,
                suspension_reason=''
            )
            self.last_check = now
        
        return self.get_response(request)
    
# في نهاية users/middleware.py

class PaymentCheckMiddleware:
    """
    Middleware لفحص الدفعات المعلقة بشكل دوري
    Periodically check for pending payments
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # فحص الدفعات المعلقة قبل معالجة الـ request
        # يتم الفحص كل 24 ساعة تلقائياً
        trigger_payment_check_if_needed()
        
        response = self.get_response(request)
        return response