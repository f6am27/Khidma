# notifications/management/commands/check_pending_payments.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tasks.models import ServiceRequest
from notifications.admin_signals import create_admin_notification


class Command(BaseCommand):
    help = 'Check for pending payments (tasks completed > 48h ago without payment)'

    def handle(self, *args, **kwargs):
        # حساب 48 ساعة قبل الآن
        cutoff_time = timezone.now() - timedelta(hours=48)
        
        # البحث عن المهام:
        # 1. حالتها 'work_completed' (العمل اكتمل لكن لم يتم الدفع)
        # 2. مر عليها أكثر من 48 ساعة
        # 3. لا يوجد لها دفع مكتمل
        pending_tasks = ServiceRequest.objects.filter(
            status='work_completed',
            work_completed_at__lte=cutoff_time
        ).exclude(
            payment__status='completed'
        )
        
        count = 0
        for task in pending_tasks:
            client_name = task.client.get_full_name() or task.client.phone
            worker_name = task.assigned_worker.get_full_name() if task.assigned_worker else 'Non assigné'
            
            # حساب عدد الساعات
            hours_passed = int((timezone.now() - task.work_completed_at).total_seconds() / 3600)
            
            create_admin_notification(
                notification_type='payment_pending',
                title=f'⏰ Paiement en attente: {task.title}',
                message=f'Travail terminé il y a {hours_passed}h. Client: {client_name} | Prestataire: {worker_name} | Montant: {task.budget} MRU',
                related_task=task
            )
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {count} notifications de paiement en attente créées')
        )