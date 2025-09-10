# users/management/commands/create_sample_workers.py
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User, WorkerProfile
from services.models import ServiceCategory
import random
from datetime import time


class Command(BaseCommand):
    help = 'Create sample workers with Mauritanian names and French service descriptions'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample workers...')
        
        # التأكد من وجود فئات الخدمات
        if not ServiceCategory.objects.filter(is_active=True).exists():
            self.stdout.write(
                self.style.ERROR('No service categories found. Run "python manage.py init_services_data" first.')
            )
            return
        
        with transaction.atomic():
            self.create_workers()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created 10 sample workers!')
        )
    
    def create_workers(self):
        # أسماء موريتانية واقعية
        worker_data = [
            {
                'first_name': 'Omer',
                'last_name': 'Ba',
                'phone': '+22245612345',
                'categories': ['Plomberie', 'Électricité'],
                'area': 'Tevragh Zeina',
                'price': 300,
                'description': 'Plombier expérimenté avec 8 ans d\'expérience. Intervention rapide et travail de qualité.'
            },
            {
                'first_name': 'Fatimata',
                'last_name': 'Mint Ahmed',
                'phone': '+22245612346',
                'categories': ['Nettoyage Maison', 'Blanchisserie'],
                'area': 'Riad',
                'price': 200,
                'description': 'Service de nettoyage professionnel. Disponible pour ménage quotidien et grand nettoyage.'
            },
            {
                'first_name': 'Hassan',
                'last_name': 'Ould Mohamed',
                'phone': '+22245612347',
                'categories': ['Peinture', 'Carrelage'],
                'area': 'Arafat',
                'price': 250,
                'description': 'Peintre professionnel spécialisé en décoration intérieure et extérieure.'
            },
            {
                'first_name': 'Ali',
                'last_name': 'Diallo',
                'phone': '+22245612348',
                'categories': ['Menuiserie', 'Plâtrerie'],
                'area': 'Dar Naim',
                'price': 350,
                'description': 'Menuisier qualifié pour fabrication et réparation de meubles sur mesure.'
            },
            {
                'first_name': 'Boubakren',
                'last_name': 'Sow',
                'phone': '+22245612349',
                'categories': ['Livraison', 'Déménagement'],
                'area': 'Tojounin',
                'price': 150,
                'description': 'Service de livraison et déménagement. Véhicule disponible 7j/7.'
            },
            {
                'first_name': 'Fatou',
                'last_name': 'Kane',
                'phone': '+22245612350',
                'categories': ['Garde d\'enfants', 'Aide aux Devoirs'],
                'area': 'Leksar',
                'price': 180,
                'description': 'Garde d\'enfants expérimentée et aide aux devoirs pour tous niveaux.'
            },
            {
                'first_name': 'Ahmed',
                'last_name': 'Vall',
                'phone': '+22245612351',
                'categories': ['Jardinage', 'Climatisation'],
                'area': 'Sixième',
                'price': 280,
                'description': 'Entretien de jardins et réparation de climatiseurs. Service professionnel.'
            },
            {
                'first_name': 'Mariem',
                'last_name': 'Mint Sidi',
                'phone': '+22245612352',
                'categories': ['Traiteur', 'Cuisine Quotidienne'],
                'area': 'Socogim',
                'price': 220,
                'description': 'Cuisinière traditionnelle mauritanienne. Spécialiste en plats locaux et événements.'
            },
            {
                'first_name': 'Abdellahi',
                'last_name': 'Ould Cheikh',
                'phone': '+22245612353',
                'categories': ['Réparation Téléphone', 'Réparation Ordinateur'],
                'area': 'Hay Saken',
                'price': 120,
                'description': 'Technicien en réparation électronique. Téléphones, ordinateurs et tablettes.'
            },
            {
                'first_name': 'Khadija',
                'last_name': 'Barry',
                'phone': '+22245612354',
                'categories': ['Coiffure à Domicile', 'Maquillage'],
                'area': 'Carrefour',
                'price': 160,
                'description': 'Coiffeuse professionnelle et maquilleuse. Service à domicile pour événements.'
            }
        ]
        
        # أيام العمل المختلفة
        days_options = [
            ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
            ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        ]
        
        # ساعات العمل المختلفة
        time_options = [
            (time(8, 0), time(17, 0)),    # 8h-17h
            (time(9, 0), time(18, 0)),    # 9h-18h
            (time(7, 0), time(16, 0)),    # 7h-16h
            (time(10, 0), time(19, 0)),   # 10h-19h
        ]
        
        for data in worker_data:
            # إنشاء User
            user = User.objects.create_user(
                identifier=data['phone'],
                password='worker123',  # كلمة مرور موحدة للاختبار
                role='worker',
                first_name=data['first_name'],
                last_name=data['last_name'],
                is_verified=True,
                onboarding_completed=True
            )
            
            # اختيار فئة خدمة عشوائية من القائمة المخصصة
            available_categories = ServiceCategory.objects.filter(
                name__in=data['categories'],
                is_active=True
            )
            
            if available_categories.exists():
                selected_category = random.choice(available_categories)
                
                # اختيار أيام وساعات عمل عشوائية
                selected_days = random.choice(days_options)
                start_time, end_time = random.choice(time_options)
                
                # إنشاء WorkerProfile
                WorkerProfile.objects.create(
                    user=user,
                    bio=data['description'],
                    service_area=data['area'],
                    service_category=selected_category.name,
                    base_price=data['price'],
                    available_days=selected_days,
                    work_start_time=start_time,
                    work_end_time=end_time,
                    is_verified=True,
                    is_available=True,
                    is_online=random.choice([True, False]),
                    average_rating=round(random.uniform(3.5, 5.0), 1),
                    total_jobs_completed=random.randint(5, 50),
                    total_reviews=random.randint(3, 25)
                )
                
                self.stdout.write(
                    f'Created worker: {data["first_name"]} {data["last_name"]} - {selected_category.name}'
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped {data["first_name"]} - no matching service category found'
                    )
                )