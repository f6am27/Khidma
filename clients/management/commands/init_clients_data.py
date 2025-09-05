# clients/management/commands/init_clients_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from decimal import Decimal

from accounts.models import Profile
from workers.models import WorkerProfile
from clients.models import ClientProfile, FavoriteWorker, ClientNotification, ClientSettings


class Command(BaseCommand):
    help = 'Initialize sample data for clients app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing client data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing client data...')
            ClientProfile.objects.all().delete()
            FavoriteWorker.objects.all().delete()
            ClientNotification.objects.all().delete()
            ClientSettings.objects.all().delete()

        self.stdout.write('Creating client profiles...')
        self.create_client_profiles()
        
        self.stdout.write('Creating favorite workers relationships...')
        self.create_favorite_workers()
        
        self.stdout.write('Creating client notifications...')
        self.create_client_notifications()
        
        self.stdout.write('Creating client settings...')
        self.create_client_settings()

        self.stdout.write(
            self.style.SUCCESS('Successfully initialized client data!')
        )

    def create_client_profiles(self):
        """Create sample client profiles"""
        # Get existing client profiles
        client_profiles = Profile.objects.filter(role='client')
        
        if not client_profiles.exists():
            self.stdout.write(
                self.style.WARNING('No client profiles found. Please run init_accounts_data first.')
            )
            return

        # Sample client data to enhance existing profiles (without bio)
        client_data = [
            {
                'username': 'fatima',
                'address': 'Quartier Tevragh Zeina, Rue 42-156, Nouakchott',
                'gender': 'female',
                'emergency_contact': '+22236789013',
                'is_verified': True,
                'total_tasks_published': 12,
                'total_tasks_completed': 8,
                'total_amount_spent': Decimal('45000.00'),
            },
            {
                'username': 'ahmed_hassan',
                'address': 'Ksar, Avenue Nasseur, Immeuble Commercial, Nouakchott',
                'gender': 'male',
                'emergency_contact': '+22236789014',
                'is_verified': True,
                'total_tasks_published': 18,
                'total_tasks_completed': 15,
                'total_amount_spent': Decimal('78500.00'),
            },
            {
                'username': 'aicha_client',
                'address': 'Sebkha, Quartier 5, Maison 234, Nouakchott',
                'gender': 'female',
                'emergency_contact': '+22236789015',
                'is_verified': True,
                'total_tasks_published': 9,
                'total_tasks_completed': 7,
                'total_amount_spent': Decimal('32000.00'),
            },
            {
                'username': 'omar_client',
                'address': 'Arafat, Cité Salam, Villa 12, Nouakchott',
                'gender': 'male',
                'emergency_contact': '+22236789016',
                'is_verified': False,
                'total_tasks_published': 6,
                'total_tasks_completed': 4,
                'total_amount_spent': Decimal('18500.00'),
            },
            {
                'username': 'mariam_client',
                'address': 'Riyad, Quartier Diplomatique, Nouakchott',
                'gender': 'female',
                'emergency_contact': '+22236789017',
                'is_verified': True,
                'total_tasks_published': 15,
                'total_tasks_completed': 12,
                'total_amount_spent': Decimal('65000.00'),
            }
        ]

        for data in client_data:
            try:
                profile = Profile.objects.get(
                    user__username=data['username'], 
                    role='client'
                )
                
                # Create or update client profile
                client_profile, created = ClientProfile.objects.get_or_create(
                    profile=profile,
                    defaults={
                        'address': data['address'],
                        'gender': data['gender'],
                        'emergency_contact': data['emergency_contact'],
                        'is_verified': data['is_verified'],
                        'total_tasks_published': data['total_tasks_published'],
                        'total_tasks_completed': data['total_tasks_completed'],
                        'total_amount_spent': data['total_amount_spent'],
                        'preferred_language': 'fr',
                        'notifications_enabled': True,
                        'email_notifications': True,
                        'sms_notifications': random.choice([True, False]),
                        'is_active': True,
                        'last_activity': timezone.now() - timedelta(
                            hours=random.randint(1, 48)
                        ),
                    }
                )
                
                if created:
                    self.stdout.write(f'✓ Created client profile for {data["username"]}')
                else:
                    # Update existing profile
                    for key, value in data.items():
                        if key != 'username':
                            setattr(client_profile, key, value)
                    client_profile.save()
                    self.stdout.write(f'✓ Updated client profile for {data["username"]}')
                    
            except Profile.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Profile {data["username"]} not found, skipping...')
                )

    def create_favorite_workers(self):
        """Create favorite worker relationships"""
        client_profiles = Profile.objects.filter(role='client')
        worker_profiles = WorkerProfile.objects.filter(is_available=True)
        
        if not client_profiles.exists() or not worker_profiles.exists():
            self.stdout.write(
                self.style.WARNING('No clients or workers found for creating favorites.')
            )
            return

        # Define specific favorite relationships
        favorite_relationships = [
            # Fatima's favorites
            {
                'client_username': 'fatima',
                'worker_usernames': ['fatima_worker', 'ahmed_worker', 'omar_worker'],
                'notes': [
                    'Excellent travail de nettoyage, très minutieuse',
                    'Plombier fiable, prix raisonnables',
                    'Très bon jardinier, ponctuel'
                ]
            },
            # Ahmed Hassan's favorites
            {
                'client_username': 'ahmed_hassan',
                'worker_usernames': ['fatima_worker', 'aicha_worker', 'hassan_worker'],
                'notes': [
                    'Parfait pour l\'entretien du bureau',
                    'Garde d\'enfants de confiance',
                    'Excellent électricien'
                ]
            },
            # Aicha's favorites
            {
                'client_username': 'aicha_client',
                'worker_usernames': ['omar_worker', 'mohamed_worker'],
                'notes': [
                    'Jardinier expérimenté, bon conseil',
                    'Service de livraison rapide'
                ]
            },
            # Omar's favorites
            {
                'client_username': 'omar_client',
                'worker_usernames': ['fatima_worker', 'ahmed_worker'],
                'notes': [
                    'Service de nettoyage régulier',
                    'Dépannage rapide'
                ]
            },
            # Mariam's favorites
            {
                'client_username': 'mariam_client',
                'worker_usernames': ['aicha_worker', 'fatima_worker', 'amina_worker'],
                'notes': [
                    'Excellente baby-sitter, enfants l\'adorent',
                    'Nettoyage impeccable',
                    'Très patiente avec les enfants'
                ]
            }
        ]

        for relationship in favorite_relationships:
            try:
                client = Profile.objects.get(
                    user__username=relationship['client_username'],
                    role='client'
                )
                
                for i, worker_username in enumerate(relationship['worker_usernames']):
                    try:
                        worker = WorkerProfile.objects.get(
                            profile__user__username=worker_username
                        )
                        
                        # Create favorite with interaction history
                        favorite, created = FavoriteWorker.objects.get_or_create(
                            client=client,
                            worker=worker,
                            defaults={
                                'notes': relationship['notes'][i] if i < len(relationship['notes']) else '',
                                'times_hired': random.randint(1, 8),
                                'total_spent_with_worker': Decimal(str(random.randint(2000, 15000))),
                                'last_rating_given': random.randint(4, 5),
                                'added_at': timezone.now() - timedelta(
                                    days=random.randint(7, 180)
                                ),
                                'last_contacted': timezone.now() - timedelta(
                                    days=random.randint(1, 30)
                                )
                            }
                        )
                        
                        if created:
                            self.stdout.write(
                                f'✓ Added {worker_username} to {relationship["client_username"]} favorites'
                            )
                    
                    except WorkerProfile.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Worker {worker_username} not found')
                        )
                        
            except Profile.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Client {relationship["client_username"]} not found')
                )

    def create_client_notifications(self):
        """Create sample client notifications"""
        client_profiles = Profile.objects.filter(role='client')
        
        if not client_profiles.exists():
            return

        notification_templates = [
            {
                'type': 'task_published',
                'title': 'Tâche publiée avec succès',
                'message': 'Votre demande "{}" a été publiée et est maintenant visible par les prestataires.',
            },
            {
                'type': 'worker_applied',
                'title': 'Nouvelle candidature reçue',
                'message': '{} souhaite effectuer votre tâche "{}". Consultez son profil et acceptez l\'offre.',
            },
            {
                'type': 'task_completed',
                'title': 'Service terminé',
                'message': '{} a marqué votre tâche "{}" comme terminée. Confirmez et effectuez le paiement.',
            },
            {
                'type': 'payment_reminder',
                'title': 'Rappel de paiement',
                'message': 'N\'oubliez pas d\'effectuer le paiement pour votre service "{}" avec {}.',
            },
            {
                'type': 'system_update',
                'title': 'Mise à jour de l\'application',
                'message': 'Une nouvelle version de Khidma est disponible avec des améliorations de performance.',
            }
        ]

        task_titles = [
            'Nettoyage de maison', 'Réparation plomberie', 'Garde d\'enfants',
            'Jardinage', 'Livraison courses', 'Peinture salon'
        ]
        
        worker_names = [
            'Fatima Al-Zahra', 'Ahmed Hassan', 'Omar Ba', 
            'Aicha Mint Salem', 'Mohamed Ould Ahmed'
        ]

        for client in client_profiles:
            # Create 3-7 notifications per client
            num_notifications = random.randint(3, 7)
            
            for _ in range(num_notifications):
                template = random.choice(notification_templates)
                
                # Fill in template variables
                if '{}' in template['message']:
                    if template['type'] in ['task_published', 'task_completed', 'payment_reminder']:
                        task_title = random.choice(task_titles)
                        if template['type'] == 'task_published':
                            message = template['message'].format(task_title)
                        else:
                            worker_name = random.choice(worker_names)
                            message = template['message'].format(worker_name, task_title)
                    elif template['type'] == 'worker_applied':
                        worker_name = random.choice(worker_names)
                        task_title = random.choice(task_titles)
                        message = template['message'].format(worker_name, task_title)
                    else:
                        message = template['message']
                else:
                    message = template['message']
                
                # Create notification
                created_at = timezone.now() - timedelta(
                    hours=random.randint(1, 168)  # Last week
                )
                
                notification = ClientNotification.objects.create(
                    client=client,
                    notification_type=template['type'],
                    title=template['title'],
                    message=message,
                    is_read=random.choice([True, False]),
                    created_at=created_at
                )
                
                # Set read_at for read notifications
                if notification.is_read:
                    notification.read_at = created_at + timedelta(
                        minutes=random.randint(5, 1440)
                    )
                    notification.save()

        self.stdout.write(f'✓ Created notifications for {client_profiles.count()} clients')

    def create_client_settings(self):
        """Create client settings"""
        client_profiles = Profile.objects.filter(role='client')
        
        if not client_profiles.exists():
            return

        languages = ['fr', 'ar', 'en']
        themes = ['light', 'dark', 'auto']
        visibility_options = ['public', 'workers_only', 'private']

        for client in client_profiles:
            settings, created = ClientSettings.objects.get_or_create(
                client=client,
                defaults={
                    'push_notifications': random.choice([True, False]),
                    'email_notifications': random.choice([True, False]),
                    'sms_notifications': random.choice([True, False]),
                    'theme_preference': random.choice(themes),
                    'language': random.choice(languages),
                    'profile_visibility': random.choice(visibility_options),
                    'show_last_seen': random.choice([True, False]),
                    'allow_contact_from_workers': random.choice([True, False]),
                    'auto_detect_location': random.choice([True, False]),
                    'search_radius_km': random.choice([5, 10, 15, 20]),
                }
            )
            
            if created:
                self.stdout.write(f'✓ Created settings for {client.user.username}')

        self.stdout.write(f'✓ Created settings for {client_profiles.count()} clients')