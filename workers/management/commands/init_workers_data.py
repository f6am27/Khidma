# workers/management/commands/init_workers_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile
from workers.models import WorkerProfile, WorkerService
from services.models import ServiceCategory
import random
from datetime import time


class Command(BaseCommand):
    help = 'Create sample workers with profiles and services'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample workers...')
        
        # Sample worker data matching what you had in Flutter
        workers_data = [
            {
                'username': 'fatima_cleaning',
                'first_name': 'Fatima',
                'last_name': 'Al-Zahra',
                'phone': '+22232001001',
                'bio': 'Experte en nettoyage résidentiel avec 5 ans d\'expérience. Je fournis mes propres produits écologiques.',
                'service_area': 'Tevragh Zeina, Nouakchott',
                'services': [{'category': 'Nettoyage Maison', 'price': 2500}],
                'rating': 4.9,
                'jobs': 87,
                'reviews': 124,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'hours': (time(8, 0), time(17, 0)),
                'verified': True,
                'online': True
            },
            {
                'username': 'ahmed_plombier',
                'first_name': 'Ahmed',
                'last_name': 'Hassan',
                'phone': '+22232001002',
                'bio': 'Plombier professionnel, intervention rapide 24h/24. Spécialisé dans les urgences.',
                'service_area': 'Ksar, Nouakchott',
                'services': [
                    {'category': 'Plomberie', 'price': 3000},
                    {'category': 'Électricité', 'price': 3500}
                ],
                'rating': 4.8,
                'jobs': 156,
                'reviews': 98,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
                'hours': (time(7, 0), time(19, 0)),
                'verified': True,
                'online': False
            },
            {
                'username': 'omar_electricien',
                'first_name': 'Omar',
                'last_name': 'Ba',
                'phone': '+22232001003',
                'bio': 'Électricien certifié, installation et réparation. Matériel de qualité garanti.',
                'service_area': 'Sebkha, Nouakchott',
                'services': [
                    {'category': 'Électricité', 'price': 2800},
                    {'category': 'Jardinage', 'price': 1800}
                ],
                'rating': 4.7,
                'jobs': 43,
                'reviews': 67,
                'days': ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
                'hours': (time(8, 30), time(16, 30)),
                'verified': False,
                'online': True
            },
            {
                'username': 'aicha_babysitter',
                'first_name': 'Aicha',
                'last_name': 'Mint Salem',
                'phone': '+22232001004',
                'bio': 'Garde d\'enfants expérimentée, diplômée en puériculture. Références disponibles.',
                'service_area': 'Arafat, Nouakchott',
                'services': [
                    {'category': 'Garde d\'enfants', 'price': 2000},
                    {'category': 'Aide aux Devoirs', 'price': 1500}
                ],
                'rating': 4.6,
                'jobs': 72,
                'reviews': 89,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'hours': (time(7, 0), time(18, 0)),
                'verified': True,
                'online': False
            },
            {
                'username': 'hassan_jardinier',
                'first_name': 'Hassan',
                'last_name': 'Ould Baba',
                'phone': '+22232001005',
                'bio': 'Jardinier paysagiste, entretien d\'espaces verts. Taille, plantation, arrosage.',
                'service_area': 'Riad, Nouakchott',
                'services': [
                    {'category': 'Jardinage', 'price': 2200},
                    {'category': 'Nettoyage Maison', 'price': 2000}
                ],
                'rating': 4.5,
                'jobs': 58,
                'reviews': 76,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'saturday'],
                'hours': (time(6, 0), time(15, 0)),
                'verified': True,
                'online': True
            },
            {
                'username': 'mariem_peintre',
                'first_name': 'Mariem',
                'last_name': 'Ba',
                'phone': '+22232001006',
                'bio': 'Peinture intérieure et extérieure, finitions de qualité. Devis gratuit.',
                'service_area': 'Dar Naim, Nouakchott',
                'services': [
                    {'category': 'Peinture', 'price': 4000},
                    {'category': 'Menuiserie', 'price': 3500}
                ],
                'rating': 4.4,
                'jobs': 34,
                'reviews': 52,
                'days': ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'hours': (time(8, 0), time(17, 0)),
                'verified': False,
                'online': False
            },
            {
                'username': 'mohamed_menuisier',
                'first_name': 'Mohamed',
                'last_name': 'Ould Ahmed',
                'phone': '+22232001007',
                'bio': 'Menuisier ébéniste, mobilier sur mesure et réparations. Travail artisanal.',
                'service_area': 'Tojounin, Nouakchott',
                'services': [
                    {'category': 'Menuiserie', 'price': 3800},
                    {'category': 'Peinture', 'price': 3200}
                ],
                'rating': 4.8,
                'jobs': 91,
                'reviews': 115,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
                'hours': (time(7, 30), time(18, 30)),
                'verified': True,
                'online': True
            },
            {
                'username': 'khadija_traiteur',
                'first_name': 'Khadija',
                'last_name': 'Mint Mohamed',
                'phone': '+22232001008',
                'bio': 'Traiteur spécialisée cuisine mauritanienne traditionnelle. Événements et quotidien.',
                'service_area': 'Leksar, Nouakchott',
                'services': [
                    {'category': 'Traiteur', 'price': 5000},
                    {'category': 'Cuisine Quotidienne', 'price': 3000}
                ],
                'rating': 4.9,
                'jobs': 128,
                'reviews': 156,
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'hours': (time(6, 0), time(20, 0)),
                'verified': True,
                'online': False
            }
        ]
        
        created_workers = []
        
        for worker_data in workers_data:
            try:
                # Create or get user
                user, user_created = User.objects.get_or_create(
                    username=worker_data['username'],
                    defaults={
                        'first_name': worker_data['first_name'],
                        'last_name': worker_data['last_name'],
                        'is_active': True
                    }
                )
                
                if user_created:
                    user.set_password('worker123')  # Default password for testing
                    user.save()
                
                # Create or get profile
                profile, profile_created = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'phone': worker_data['phone'],
                        'phone_verified': True,
                        'role': Profile.ROLE_WORKER,
                        'onboarding_completed': True  # Important!
                    }
                )
                
                # Create or update worker profile
                worker_profile, wp_created = WorkerProfile.objects.get_or_create(
                    profile=profile,
                    defaults={
                        'bio': worker_data['bio'],
                        'service_area': worker_data['service_area'],
                        'available_days': worker_data['days'],
                        'work_start_time': worker_data['hours'][0],
                        'work_end_time': worker_data['hours'][1],
                        'total_jobs_completed': worker_data['jobs'],
                        'average_rating': worker_data['rating'],
                        'total_reviews': worker_data['reviews'],
                        'is_verified': worker_data['verified'],
                        'is_available': True,
                        'is_online': worker_data['online'],
                    }
                )
                
                # Create services
                for service_data in worker_data['services']:
                    try:
                        category = ServiceCategory.objects.get(name=service_data['category'])
                        
                        WorkerService.objects.get_or_create(
                            worker=worker_profile,
                            category=category,
                            defaults={
                                'base_price': service_data['price'],
                                'price_type': 'negotiable',
                                'description': f"Service {category.name} professionnel",
                                'is_active': True,
                                'min_duration_hours': 1
                            }
                        )
                    except ServiceCategory.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Service category "{service_data["category"]}" not found')
                        )
                
                created_workers.append(worker_data['username'])
                self.stdout.write(f'Created worker: {worker_data["username"]}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating worker {worker_data["username"]}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_workers)} sample workers!')
        )
        
        # Display summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('WORKERS CREATED:')
        self.stdout.write('='*50)
        for worker in created_workers:
            self.stdout.write(f'✓ {worker}')
        
        self.stdout.write('\n' + 'LOGIN INFO:')
        self.stdout.write('- Username: [worker_username]')
        self.stdout.write('- Password: worker123')
        self.stdout.write('\nWorkers are ready for API testing!')