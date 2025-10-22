# users/management/commands/reactivate_suspended_accounts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User


class Command(BaseCommand):
    """
    أمر لإعادة تفعيل الحسابات المعلقة التي انتهت مدة تعليقها
    Command to reactivate suspended accounts after suspension period ends
    """
    help = 'إعادة تفعيل الحسابات المعلقة التي انتهت مدة تعليقها'
    
    def handle(self, *args, **options):
        now = timezone.now()
        
        # البحث عن الحسابات المعلقة التي انتهت مدتها
        suspended_users = User.objects.filter(
            is_suspended=True,
            suspended_until__lte=now,  # تاريخ التعليق انتهى
            suspended_until__isnull=False  # ليس إيقاف نهائي
        )
        
        count = suspended_users.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ لا توجد حسابات معلقة لإعادة تفعيلها')
            )
            return
        
        # عرض الحسابات التي سيتم تفعيلها
        self.stdout.write(f'\n🔄 جاري إعادة تفعيل {count} حساب...\n')
        
        for user in suspended_users:
            self.stdout.write(
                f'  ✓ @{user.username} - تم التعليق: {user.suspension_reason[:50]}'
            )
            
            # إعادة التفعيل
            user.is_active = True
            user.is_suspended = False
            user.suspended_until = None
            user.suspension_reason = ''
            user.save()
            
            # TODO: إرسال إشعار للمستخدم بإعادة تفعيل حسابه
            # send_notification(user, 'ACCOUNT_REACTIVATED')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ تم إعادة تفعيل {count} حساب بنجاح!')
        )