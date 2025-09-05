# tasks/management/commands/init_tasks_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

from accounts.models import Profile
from workers.models import WorkerProfile
from services.models import ServiceCategory
from tasks.models import ServiceRequest, TaskApplication, TaskReview, TaskNotification


class Command(BaseCommand):
    help = 'Create sample tasks and applications for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample tasks and applications...')
        
        # Get existing users and profiles
        clients = Profile.objects.filter(role='client', onboarding_completed=True)
        workers = WorkerProfile.objects.filter(
            is_available=True,
            profile__onboarding_completed=True
        )
        categories = ServiceCategory.objects.filter(is_active=True)
        
        if not clients.exists():
            self.stdout.write(
                self.style.ERROR('No clients found. Please create client accounts first.')
            )
            return
        
        if not workers.exists():
            self.stdout.write(
                self.style.ERROR('No workers found. Please run init_workers_data first.')
            )
            return
        
        self.create_sample_tasks(clients, categories, workers)
        self.stdout.write(self.style.SUCCESS('Successfully created sample tasks!'))
    
    def create_sample_tasks(self, clients, categories, workers):
        # Sample task data with proper time formats
        tasks_data = [
            # Published tasks (with applications)
            {
                'title': 'Nettoyage appartement 3 pièces',
                'description': 'Nettoyage complet d\'un appartement de 3 pièces avec cuisine et salle de bain. Produits fournis. Travail soigné demandé.',
                'category': 'Nettoyage Maison',
                'budget': 5000,
                'location': 'Tevragh Zeina, Nouakchott',
                'preferred_time': '9:00 AM',
                'status': 'published',
                'is_urgent': False,
                'has_applications': True,
                'created_days_ago': 0
            },
            {
                'title': 'Réparation robinet cuisine',
                'description': 'Réparation d\'un robinet qui fuit dans la cuisine. Intervention urgente nécessaire.',
                'category': 'Plomberie',
                'budget': 2000,
                'location': 'Ksar, Nouakchott',
                'preferred_time': '2:00 PM',
                'status': 'published',
                'is_urgent': True,
                'has_applications': True,
                'created_days_ago': 1
            },
            {
                'title': 'Installation électrique nouvelle prise',
                'description': 'Installation d\'une nouvelle prise électrique dans le salon. Matériel à fournir par le prestataire.',
                'category': 'Électricité',
                'budget': 1500,
                'location': 'Sebkha, Nouakchott',
                'preferred_time': '10:00 AM',
                'status': 'published',
                'is_urgent': False,
                'has_applications': True,
                'created_days_ago': 2
            },
            
            # Active tasks (assigned workers)
            {
                'title': 'Peinture salon',
                'description': 'Peinture du salon avec couleur beige. Surface environ 25m². Peinture fournie.',
                'category': 'Peinture',
                'budget': 8000,
                'location': 'Sebkha, Nouakchott',
                'preferred_time': '8:00 AM',
                'status': 'active',
                'is_urgent': False,
                'has_applications': False,
                'created_days_ago': 3
            },
            {
                'title': 'Réparation porte d\'entrée',
                'description': 'Réparation de la serrure et ajustement de la porte d\'entrée qui ferme mal.',
                'category': 'Menuiserie',
                'budget': 3500,
                'location': 'Riad, Nouakchott',
                'preferred_time': '1:30 PM',
                'status': 'active',
                'is_urgent': False,
                'has_applications': False,
                'created_days_ago': 5
            },
            
            # Completed tasks
            {
                'title': 'Jardinage et tonte',
                'description': 'Tonte de pelouse et taille des arbustes dans jardin de villa.',
                'category': 'Jardinage',
                'budget': 3000,
                'location': 'Arafat, Nouakchott',
                'preferred_time': '7:00 AM',
                'status': 'completed',
                'is_urgent': False,
                'has_applications': False,
                'created_days_ago': 7
            },
            {
                'title': 'Nettoyage après déménagement',
                'description': 'Nettoyage complet d\'un appartement après déménagement. Grand nettoyage nécessaire.',
                'category': 'Nettoyage Maison',
                'budget': 4500,
                'location': 'Tevragh Zeina, Nouakchott',
                'preferred_time': 'Matin',
                'status': 'completed',
                'is_urgent': False,
                'has_applications': False,
                'created_days_ago': 10
            },
            
            # Cancelled tasks
            {
                'title': 'Déménagement studio',
                'description': 'Déménagement d\'un studio vers nouvel appartement. Aide pour transport mobilier.',
                'category': 'Déménagement',
                'budget': 15000,
                'location': 'Dar Naim, Nouakchott',
                'preferred_time': '4:00 PM',
                'status': 'cancelled',
                'is_urgent': False,
                'has_applications': False,
                'created_days_ago': 10
            },
            
            # Additional published tasks with different time formats
            {
                'title': 'Réparation climatisation',
                'description': 'Réparation et maintenance d\'un climatiseur split. Problème de refroidissement.',
                'category': 'Climatisation',
                'budget': 3500,
                'location': 'Tevragh Zeina, Nouakchott',
                'preferred_time': '11:30 AM',
                'status': 'published',
                'is_urgent': True,
                'has_applications': True,
                'created_days_ago': 0
            },
            {
                'title': 'Cuisine quotidienne',
                'description': 'Préparation de repas traditionnels mauritaniens pour une famille de 6 personnes.',
                'category': 'Cuisine Quotidienne',
                'budget': 2800,
                'location': 'Ksar, Nouakchott',
                'preferred_time': '5:30 PM',
                'status': 'published',
                'is_urgent': False,
                'has_applications': True,
                'created_days_ago': 1
            }
        ]
        
        created_tasks = []
        
        for task_data in tasks_data:
            try:
                # Get category
                category = categories.filter(name=task_data['category']).first()
                if not category:
                    self.stdout.write(f"Category {task_data['category']} not found, skipping...")
                    continue
                
                # Get random client
                client = random.choice(clients)
                
                # Create task
                created_at = timezone.now() - timedelta(days=task_data['created_days_ago'])
                
                task = ServiceRequest.objects.create(
                    client=client,
                    title=task_data['title'],
                    description=task_data['description'],
                    service_category=category,
                    budget=task_data['budget'],
                    location=task_data['location'],
                    preferred_time=task_data['preferred_time'],
                    status=task_data['status'],
                    is_urgent=task_data['is_urgent'],
                    requires_materials=True,
                    created_at=created_at,
                    updated_at=created_at
                )
                
                # Handle different statuses
                if task_data['status'] == 'active':
                    # Assign random worker
                    suitable_workers = workers.filter(
                        services__category=category
                    ).distinct()
                    
                    if suitable_workers.exists():
                        worker = random.choice(suitable_workers)
                        task.assigned_worker = worker
                        task.accepted_at = created_at + timedelta(hours=random.randint(1, 24))
                        task.save()
                
                elif task_data['status'] == 'completed':
                    # Assign worker and set completion times
                    suitable_workers = workers.filter(
                        services__category=category
                    ).distinct()
                    
                    if suitable_workers.exists():
                        worker = random.choice(suitable_workers)
                        task.assigned_worker = worker
                        task.accepted_at = created_at + timedelta(hours=random.randint(1, 12))
                        task.work_completed_at = task.accepted_at + timedelta(hours=random.randint(2, 48))
                        task.completed_at = task.work_completed_at + timedelta(hours=random.randint(1, 12))
                        task.final_price = task.budget + random.randint(-500, 500)
                        task.save()
                        
                        # Create review
                        self.create_sample_review(task)
                
                elif task_data['status'] == 'cancelled':
                    task.cancelled_at = created_at + timedelta(hours=random.randint(1, 72))
                    task.save()
                
                # Create applications for published tasks
                if task_data['has_applications'] and task_data['status'] == 'published':
                    self.create_sample_applications(task, workers, category)
                
                created_tasks.append(task_data['title'])
                self.stdout.write(f'Created task: {task_data["title"]}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating task {task_data["title"]}: {str(e)}')
                )
        
        # Create some notifications
        self.create_sample_notifications(created_tasks)
        
        self.stdout.write(f'Created {len(created_tasks)} tasks successfully!')
    
    def create_sample_applications(self, task, workers, category):
        """Create sample applications for a task (simplified without price and availability)"""
        # Find workers who can do this service
        suitable_workers = workers.filter(
            services__category=category
        ).distinct()
        
        # Create 1-4 applications (but not more than available workers)
        max_applications = min(4, len(suitable_workers))
        if max_applications == 0:
            return  # No suitable workers found
        
        num_applications = random.randint(1, max_applications)
        selected_workers = random.sample(list(suitable_workers), num_applications)
        
        messages = [
            "Je suis disponible pour cette tâche et j'ai l'expérience nécessaire.",
            "Bonjour, je peux réaliser cette mission rapidement et efficacement.",
            "J'ai plusieurs années d'expérience dans ce domaine. Je suis disponible.",
            "Mission intéressante ! Je suis libre et motivé pour la réaliser.",
            "Bonjour, je propose mes services pour cette tâche. Qualité garantie.",
            "Expérience confirmée dans ce domaine. Disponible immédiatement.",
            "Travail soigné garanti. Je suis motivé pour cette mission.",
            "",  # Empty message for some applications
        ]
        
        for i, worker in enumerate(selected_workers):
            try:
                application = TaskApplication.objects.create(
                    service_request=task,
                    worker=worker,
                    application_message=random.choice(messages),
                    applied_at=task.created_at + timedelta(
                        hours=random.randint(1, 24),
                        minutes=random.randint(0, 59)
                    )
                )
                
                self.stdout.write(f'  - Application from {worker.user.username}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error creating application for {worker.user.username}: {str(e)}')
                )
    
    def create_sample_review(self, task):
        """Create a sample review for completed task (simplified)"""
        reviews_data = [
            {
                'rating': 5,
                'review_text': 'Excellent travail ! Très professionnel et ponctuel. Je recommande vivement.',
            },
            {
                'rating': 4,
                'review_text': 'Bon travail dans l\'ensemble. Quelques petites améliorations possibles mais satisfait.',
            },
            {
                'rating': 5,
                'review_text': 'Parfait ! Travail soigné et dans les temps. Personne très aimable.',
            },
            {
                'rating': 4,
                'review_text': 'Prestation correcte. Professionnel compétent. Je referai appel à ses services.',
            },
            {
                'rating': 5,
                'review_text': '',  # Empty review text
            },
            {
                'rating': 3,
                'review_text': 'Travail correct mais quelques retards.',
            }
        ]
        
        review_data = random.choice(reviews_data)
        
        try:
            TaskReview.objects.create(
                service_request=task,
                client=task.client,
                worker=task.assigned_worker,
                rating=review_data['rating'],
                review_text=review_data['review_text'],
                would_recommend=review_data['rating'] >= 4,
                is_public=True
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error creating review: {str(e)}')
            )
    
    def create_sample_notifications(self, created_tasks):
        """Create sample notifications"""
        # Get some profiles for notifications
        profiles = Profile.objects.filter(onboarding_completed=True)[:5]
        
        notification_types = [
            ('task_posted', 'Nouvelle tâche disponible'),
            ('application_received', 'Nouvelle candidature reçue'),
            ('application_accepted', 'Candidature acceptée'),
            ('work_completed', 'Travail terminé'),
            ('task_completed', 'Tâche confirmée terminée'),
        ]
        
        for profile in profiles:
            # Create 2-3 notifications per profile
            for i in range(random.randint(2, 3)):
                notif_type, title = random.choice(notification_types)
                
                TaskNotification.objects.create(
                    recipient=profile,
                    notification_type=notif_type,
                    title=title,
                    message=f'Notification de test pour {profile.user.username}',
                    is_read=random.choice([True, False]),
                    is_sent=True,
                    sent_at=timezone.now() - timedelta(
                        hours=random.randint(1, 48)
                    )
                )