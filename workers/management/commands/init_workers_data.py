# workers/management/commands/init_workers_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile
from services.models import ServiceCategory
from workers.models import WorkerProfile, WorkerService
import random
from datetime import time

class Command(BaseCommand):
    help = 'Create sample workers for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample workers...')
        self.create_workers()
        self.stdout.write(self.style.SUCCESS('Successfully created sample workers!'))

    def create_workers(self):
        # Sample worker data - بيانات عمال وهمية
        workers_data = [
            {
                'username': 'fatima_cleaning',
                'email': 'fatima@test.com',
                'phone': '+22236789012',
                'bio': 'Service de nettoyage professionnel avec 5 ans d\'expérience',
                'service_area': 'Tevragh Zeina',
                'services': [
                    {'category': 'Nettoyage Maison', 'price': 2500.0, 'type': 'fixed'},
                    {'category': 'Blanchisserie', 'price': 1800.0, 'type': 'fixed'},
                ],
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'start_time': time(8, 0),
                'end_time': time(17, 0),
                'rating': 4.8,
                'reviews': 45,
                'completed_jobs': 67,
            },
            {
                'username': 'ahmed_plombier',
                'email': 'ahmed@test.com', 
                'phone': '+22237890123',
                'bio': 'Plombier expérimenté, intervention rapide 24h/24',
                'service_area': 'Ksar',
                'services': [
                    {'category': 'Plomberie', 'price': 3500.0, 'type': 'hourly'},
                ],
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
                'start_time': time(7, 0),
                'end_time': time(19, 0),
                'rating': 4.9,
                'reviews': 67,
                'completed_jobs': 89,
            },
            {
                'username': 'omar_electricien',
                'email': 'omar@test.com',
                'phone': '+22238901234',
                'bio': 'Électricien certifié, installation et dépannage électrique',
                'service_area': 'Riad',
                'services': [
                    {'category': 'Électricité', 'price': 4000.0, 'type': 'hourly'},
                    {'category': 'Climatisation', 'price': 5500.0, 'type': 'fixed'},
                ],
                'days': ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
                'start_time': time(9, 0),
                'end_time': time(18, 0),
                'rating': 4.6,
                'reviews': 34,
                'completed_jobs': 45,
            },
            {
                'username': 'aicha_babysitter',
                'email': 'aicha@test.com',
                'phone': '+22239012345',
                'bio': 'Garde d\'enfants expérimentée, disponible en soirée et weekends',
                'service_area': 'Sebkha',
                'services': [
                    {'category': 'Garde d\'enfants', 'price': 2000.0, 'type': 'hourly'},
                    {'category': 'Aide aux Devoirs', 'price': 1500.0, 'type': 'hourly'},
                ],
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'start_time': time(14, 0),
                'end_time': time(22, 0),
                'rating': 4.7,
                'reviews': 28,
                'completed_jobs': 38,
            },
            {
                'username': 'hassan_jardinier',
                'email': 'hassan@test.com',
                'phone': '+22240123456',
                'bio': 'Jardinier professionnel, entretien espaces verts et jardinage',
                'service_area': 'Arafat',
                'services': [
                    {'category': 'Jardinage', 'price': 3000.0, 'type': 'fixed'},
                ],
                'days': ['monday', 'wednesday', 'friday', 'saturday'],
                'start_time': time(6, 30),
                'end_time': time(15, 0),
                'rating': 4.5,
                'reviews': 19,
                'completed_jobs': 25,
            },
            {
                'username': 'mariem_peintre',
                'email': 'mariem@test.com',
                'phone': '+22241234567',
                'bio': 'Peintre décoratrice, peinture intérieure et extérieure',
                'service_area': 'Dar Naim',
                'services': [
                    {'category': 'Peinture', 'price': 4500.0, 'type': 'negotiable'},
                ],
                'days': ['monday', 'tuesday', 'thursday', 'friday'],
                'start_time': time(8, 30),
                'end_time': time(16, 30),
                'rating': 4.4,
                'reviews': 22,
                'completed_jobs': 31,
            },
            {
                'username': 'mohamed_menuisier',
                'email': 'mohamed@test.com',
                'phone': '+22242345678',
                'bio': 'Menuisier spécialisé dans les meubles sur mesure',
                'service_area': 'Tojounin',
                'services': [
                    {'category': 'Menuiserie', 'price': 6000.0, 'type': 'negotiable'},
                ],
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'start_time': time(7, 0),
                'end_time': time(17, 0),
                'rating': 4.9,
                'reviews': 41,
                'completed_jobs': 52,
            },
            {
                'username': 'khadija_traiteur',
                'email': 'khadija@test.com',
                'phone': '+22243456789',
                'bio': 'Traiteur pour événements et cuisine quotidienne',
                'service_area': 'El Mina',
                'services': [
                    {'category': 'Traiteur', 'price': 8000.0, 'type': 'negotiable'},
                    {'category': 'Cuisine Quotidienne', 'price': 3500.0, 'type': 'fixed'},
                ],
                'days': ['wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                'start_time': time(10, 0),
                'end_time': time(20, 0),
                'rating': 4.8,
                'reviews': 36,
                'completed_jobs': 48,
            },
        ]

        for worker_data in workers_data:
            # Check if user already exists
            if User.objects.filter(username=worker_data['username']).exists():
                self.stdout.write(f"Worker {worker_data['username']} already exists, skipping...")
                continue

            # Create user
            user = User.objects.create_user(
                username=worker_data['username'],
                email=worker_data['email'],
                password='testpass123'  # Simple password for testing
            )

            # Create profile
            profile = Profile.objects.create(
                user=user,
                phone=worker_data['phone'],
                phone_verified=True,
                role=Profile.ROLE_WORKER,
                onboarding_completed=True
            )

            # Create worker profile
            worker_profile = WorkerProfile.objects.create(
                profile=profile,
                bio=worker_data['bio'],
                service_area=worker_data['service_area'],
                available_days=worker_data['days'],
                work_start_time=worker_data['start_time'],
                work_end_time=worker_data['end_time'],
                average_rating=worker_data['rating'],
                total_reviews=worker_data['reviews'],
                total_jobs_completed=worker_data['completed_jobs'],
                is_verified=random.choice([True, False]),
                is_available=True,
                is_online=random.choice([True, False])
            )

            # Create worker services
            for service_data in worker_data['services']:
                try:
                    category = ServiceCategory.objects.get(name=service_data['category'])
                    WorkerService.objects.create(
                        worker=worker_profile,
                        category=category,
                        base_price=service_data['price'],
                        price_type=service_data['type']
                    )
                except ServiceCategory.DoesNotExist:
                    self.stdout.write(f"Category {service_data['category']} not found, skipping service...")

            self.stdout.write(f"Created worker: {worker_data['username']}")