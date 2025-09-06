# notifications/management/commands/init_notifications_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import Profile
from notifications.models import Notification, NotificationSettings, NotificationTemplate
from workers.models import WorkerProfile
from tasks.models import ServiceRequest


class Command(BaseCommand):
    help = 'Initialize notification dummy data / إنشاء بيانات وهمية للإشعارات'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating notification dummy data...')
        
        # 1. إنشاء قوالب الإشعارات
        self.create_notification_templates()
        
        # 2. إنشاء إعدادات الإشعارات للمستخدمين
        self.create_notification_settings()
        
        # 3. إنشاء إشعارات وهمية للعملاء
        self.create_client_notifications()
        
        # 4. إنشاء إشعارات وهمية للعمال
        self.create_worker_notifications()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Notification dummy data created successfully!')
        )
    
    def create_notification_templates(self):
        """إنشاء قوالب الإشعارات"""
        templates = [
            {
                'notification_type': 'task_published',
                'title_fr': 'Tâche publiée avec succès',
                'message_fr': 'Votre demande "{task_title}" a été publiée et est maintenant visible par les prestataires.',
                'template_variables': ['task_title', 'client_name']
            },
            {
                'notification_type': 'worker_applied',
                'title_fr': 'Nouvelle candidature reçue',
                'message_fr': '{worker_name} souhaite effectuer votre tâche "{task_title}". Consultez son profil et acceptez l\'offre.',
                'template_variables': ['worker_name', 'task_title']
            },
            {
                'notification_type': 'task_completed',
                'title_fr': 'Service terminé',
                'message_fr': '{worker_name} a marqué votre tâche "{task_title}" comme terminée. Confirmez et effectuez le paiement.',
                'template_variables': ['worker_name', 'task_title']
            },
            {
                'notification_type': 'payment_received',
                'title_fr': 'Paiement confirmé',
                'message_fr': 'Votre paiement de {amount} MRU pour le service "{task_title}" a été effectué avec succès.',
                'template_variables': ['amount', 'task_title']
            },
            {
                'notification_type': 'message_received',
                'title_fr': 'Nouveau message reçu',
                'message_fr': '{sender_name} vous a envoyé un message concernant votre demande "{task_title}".',
                'template_variables': ['sender_name', 'task_title']
            },
            {
                'notification_type': 'service_reminder',
                'title_fr': 'Rappel de service',
                'message_fr': 'Votre service "{task_title}" avec {worker_name} est programmé pour {scheduled_time}. N\'oubliez pas!',
                'template_variables': ['task_title', 'worker_name', 'scheduled_time']
            },
            {
                'notification_type': 'service_cancelled',
                'title_fr': 'Service annulé',
                'message_fr': '{worker_name} a dû annuler votre rendez-vous "{task_title}" prévu pour {scheduled_time}. Il vous contactera pour reprogrammer.',
                'template_variables': ['worker_name', 'task_title', 'scheduled_time']
            },
            # قوالب إشعارات العمال
            {
                'notification_type': 'new_task_available',
                'title_fr': 'Nouvelle tâche disponible',
                'message_fr': 'Une nouvelle tâche "{task_title}" est disponible dans votre zone pour {budget} MRU.',
                'template_variables': ['task_title', 'budget']
            },
            {
                'notification_type': 'application_accepted',
                'title_fr': 'Candidature acceptée!',
                'message_fr': 'Félicitations! Votre candidature pour "{task_title}" a été acceptée par {client_name}.',
                'template_variables': ['task_title', 'client_name']
            },
            {
                'notification_type': 'application_rejected',
                'title_fr': 'Candidature non retenue',
                'message_fr': 'Votre candidature pour "{task_title}" n\'a pas été retenue cette fois. Continuez à postuler!',
                'template_variables': ['task_title']
            },
            {
                'notification_type': 'payment_sent',
                'title_fr': 'Paiement reçu',
                'message_fr': 'Vous avez reçu un paiement de {amount} MRU pour votre service "{task_title}". Merci pour votre excellent travail!',
                'template_variables': ['amount', 'task_title']
            }
        ]
        
        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                notification_type=template_data['notification_type'],
                defaults=template_data
            )
            if created:
                self.stdout.write(f'✓ Template created: {template.notification_type}')
    
    def create_notification_settings(self):
        """إنشاء إعدادات الإشعارات للمستخدمين"""
        profiles = Profile.objects.all()
        
        for profile in profiles:
            settings, created = NotificationSettings.objects.get_or_create(
                user=profile,
                defaults={
                    'notifications_enabled': True,
                    'task_notifications': True,
                    'message_notifications': True,
                    'payment_notifications': True,
                    'quiet_hours_start': '22:00:00',
                    'quiet_hours_end': '07:00:00'
                }
            )
            if created:
                self.stdout.write(f'✓ Settings created for: {profile.user.username}')
    
    def create_client_notifications(self):
        """إنشاء إشعارات وهمية للعملاء"""
        clients = Profile.objects.filter(role='client')
        workers = WorkerProfile.objects.all()
        tasks = ServiceRequest.objects.all()
        
        notification_data = [
            # إشعارات نشر المهام
            {
                'type': 'task_published',
                'context': lambda task: {
                    'task_title': task.title,
                    'client_name': task.client.user.get_full_name() or task.client.user.username
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 72)
            },
            # إشعارات تقدم العمال
            {
                'type': 'worker_applied',
                'context': lambda task, worker: {
                    'worker_name': worker.profile.user.get_full_name() or worker.profile.user.username,
                    'task_title': task.title
                },
                'priority': 'high',
                'hours_ago': lambda: random.randint(1, 48)
            },
            # إشعارات اكتمال المهام
            {
                'type': 'task_completed',
                'context': lambda task, worker: {
                    'worker_name': worker.profile.user.get_full_name() or worker.profile.user.username,
                    'task_title': task.title
                },
                'priority': 'high',
                'hours_ago': lambda: random.randint(1, 24)
            },
            # إشعارات الدفع
            {
                'type': 'payment_received',
                'context': lambda task: {
                    'amount': task.budget,
                    'task_title': task.title
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 120)
            },
            # إشعارات الرسائل
            {
                'type': 'message_received',
                'context': lambda task, worker: {
                    'sender_name': worker.profile.user.get_full_name() or worker.profile.user.username,
                    'task_title': task.title
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 12)
            },
            # إشعارات التذكير
            {
                'type': 'service_reminder',
                'context': lambda task, worker: {
                    'task_title': task.title,
                    'worker_name': worker.profile.user.get_full_name() or worker.profile.user.username,
                    'scheduled_time': 'demain à 9h00'
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 6)
            },
            # إشعارات الإلغاء
            {
                'type': 'service_cancelled',
                'context': lambda task, worker: {
                    'worker_name': worker.profile.user.get_full_name() or worker.profile.user.username,
                    'task_title': task.title,
                    'scheduled_time': 'aujourd\'hui à 14h00'
                },
                'priority': 'high',
                'hours_ago': lambda: random.randint(1, 48)
            }
        ]
        
        for client in clients:
            # 5-8 إشعارات لكل عميل
            client_tasks = tasks.filter(client=client)
            num_notifications = random.randint(5, 8)
            
            for i in range(num_notifications):
                # اختيار نوع إشعار عشوائي
                notif_type = random.choice(notification_data)
                
                # اختيار مهمة عشوائية للعميل
                if client_tasks.exists():
                    task = random.choice(client_tasks)
                    worker = random.choice(workers) if workers.exists() else None
                    
                    # تحضير بيانات السياق
                    if 'worker' in notif_type['context'].__code__.co_varnames and worker:
                        context = notif_type['context'](task, worker)
                        related_worker = worker
                    else:
                        context = notif_type['context'](task)
                        related_worker = None
                    
                    # إنشاء الإشعار
                    notification = Notification.objects.create(
                        recipient=client,
                        notification_type=notif_type['type'],
                        title_key=f"notifications.{notif_type['type']}.title",
                        message_key=f"notifications.{notif_type['type']}.message",
                        context_data=context,
                        priority=notif_type['priority'],
                        related_task=task,
                        related_worker=related_worker,
                        is_read=random.choice([True, False, False]),  # 33% مقروء
                        created_at=timezone.now() - timedelta(hours=notif_type['hours_ago']())
                    )
                    
                    # تحديد وقت القراءة للمقروءة
                    if notification.is_read:
                        notification.read_at = notification.created_at + timedelta(
                            minutes=random.randint(5, 120)
                        )
                        notification.save(update_fields=['read_at'])
        
        self.stdout.write(f'✓ Client notifications created')
    
    def create_worker_notifications(self):
        """إنشاء إشعارات وهمية للعمال"""
        workers = WorkerProfile.objects.all()
        tasks = ServiceRequest.objects.all()
        clients = Profile.objects.filter(role='client')
        
        worker_notification_data = [
            {
                'type': 'new_task_available',
                'context': lambda task: {
                    'task_title': task.title,
                    'budget': task.budget
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 24)
            },
            {
                'type': 'application_accepted',
                'context': lambda task: {
                    'task_title': task.title,
                    'client_name': task.client.user.get_full_name() or task.client.user.username
                },
                'priority': 'high',
                'hours_ago': lambda: random.randint(1, 48)
            },
            {
                'type': 'application_rejected',
                'context': lambda task: {
                    'task_title': task.title
                },
                'priority': 'low',
                'hours_ago': lambda: random.randint(1, 72)
            },
            {
                'type': 'payment_sent',
                'context': lambda task: {
                    'amount': task.budget,
                    'task_title': task.title
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 120)
            },
            {
                'type': 'message_received',
                'context': lambda task: {
                    'sender_name': task.client.user.get_full_name() or task.client.user.username,
                    'task_title': task.title
                },
                'priority': 'medium',
                'hours_ago': lambda: random.randint(1, 12)
            }
        ]
        
        for worker in workers:
            # 4-6 إشعارات لكل عامل
            num_notifications = random.randint(4, 6)
            
            for i in range(num_notifications):
                # اختيار نوع إشعار عشوائي
                notif_type = random.choice(worker_notification_data)
                
                # اختيار مهمة عشوائية
                if tasks.exists():
                    task = random.choice(tasks)
                    
                    # تحضير بيانات السياق
                    context = notif_type['context'](task)
                    
                    # تحويل Decimal إلى float في context_data
                    if 'budget' in context:
                        context['budget'] = float(context['budget'])
                    if 'amount' in context:
                        context['amount'] = float(context['amount'])
                    
                    # إنشاء الإشعار
                    notification = Notification.objects.create(
                        recipient=worker.profile,
                        notification_type=notif_type['type'],
                        title_key=f"notifications.{notif_type['type']}.title",
                        message_key=f"notifications.{notif_type['type']}.message",
                        context_data=context,
                        priority=notif_type['priority'],
                        related_task=task,
                        is_read=random.choice([True, False, False]),  # 33% مقروء
                        created_at=timezone.now() - timedelta(hours=notif_type['hours_ago']())
                    )
                    
                    # تحديد وقت القراءة للمقروءة
                    if notification.is_read:
                        notification.read_at = notification.created_at + timedelta(
                            minutes=random.randint(5, 120)
                        )
                        notification.save(update_fields=['read_at'])
        
        self.stdout.write(f'✓ Worker notifications created')
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing notification data before creating new'
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing notification data...')
            Notification.objects.all().delete()
            NotificationSettings.objects.all().delete()
            NotificationTemplate.objects.all().delete()
            self.stdout.write(self.style.WARNING('✓ Existing data cleared'))
        
        self.stdout.write('Creating notification dummy data...')
        
        # تنفيذ الخطوات
        self.create_notification_templates()
        self.create_notification_settings()
        self.create_client_notifications()
        self.create_worker_notifications()
        
        # إحصائيات نهائية
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        templates_count = NotificationTemplate.objects.count()
        settings_count = NotificationSettings.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Notification system initialized successfully!\n'
                f'📊 Statistics:\n'
                f'   • {total_notifications} notifications created\n'
                f'   • {unread_notifications} unread notifications\n'
                f'   • {templates_count} notification templates\n'
                f'   • {settings_count} user settings configured\n'
            )
        )