from django.utils import timezone
from users.models import User
from datetime import timedelta

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
