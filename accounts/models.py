from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_WORKER = 'worker'
    ROLE_CHOICES = (
        (ROLE_CLIENT, 'Client'),
        (ROLE_WORKER, 'Worker'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, unique=True)
    phone_verified = models.BooleanField(default=False)

    # ✅ جديد
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    onboarding_completed = models.BooleanField(default=False)

    # (اختياري) طوابع زمنية
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} | {self.phone} | {self.role}"
