# services/management/commands/init_services_data.py
from django.core.management.base import BaseCommand
from services.models import ServiceCategory, NouakchottArea

class Command(BaseCommand):
    help = 'Initialize services data with categories and Nouakchott areas'

    def handle(self, *args, **options):
        self.stdout.write('Creating service categories...')
        self.create_categories()
        
        self.stdout.write('Creating Nouakchott areas...')
        self.create_areas()
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized services data!'))

    def create_categories(self):
        categories = [
            # خدمات المنزل
            {'name': 'Nettoyage Maison', 'name_ar': 'تنظيف المنزل', 'icon': 'cleaning_services'},
            {'name': 'Blanchisserie', 'name_ar': 'غسيل وكي', 'icon': 'local_laundry_service'},
            {'name': 'Nettoyage Tapis', 'name_ar': 'تنظيف السجاد', 'icon': 'cleaning_services'},
            {'name': 'Jardinage', 'name_ar': 'البستنة', 'icon': 'grass'},
            {'name': 'Soins Animaux', 'name_ar': 'رعاية الحيوانات', 'icon': 'pets'},
            
            # رعاية الأطفال
            {'name': 'Garde d\'enfants', 'name_ar': 'جليسة أطفال', 'icon': 'child_care'},
            {'name': 'Transport Scolaire', 'name_ar': 'توصيل مدرسي', 'icon': 'school'},
            {'name': 'Aide aux Devoirs', 'name_ar': 'مساعدة واجبات', 'icon': 'school'},
            
            # صيانة وإصلاح
            {'name': 'Plomberie', 'name_ar': 'السباكة', 'icon': 'plumbing'},
            {'name': 'Électricité', 'name_ar': 'الكهرباء', 'icon': 'electrical_services'},
            {'name': 'Climatisation', 'name_ar': 'صيانة مكيفات', 'icon': 'ac_unit'},
            {'name': 'Réparation Téléphone', 'name_ar': 'إصلاح جوال', 'icon': 'phone_android'},
            {'name': 'Réparation Ordinateur', 'name_ar': 'إصلاح حاسوب', 'icon': 'computer'},
            {'name': 'Électroménager', 'name_ar': 'إصلاح أجهزة', 'icon': 'build'},
            
            # تجديد وبناء
            {'name': 'Peinture', 'name_ar': 'دهان المنزل', 'icon': 'format_paint'},
            {'name': 'Carrelage', 'name_ar': 'تركيب بلاط', 'icon': 'construction'},
            {'name': 'Plâtrerie', 'name_ar': 'أعمال جبس', 'icon': 'construction'},
            {'name': 'Menuiserie', 'name_ar': 'النجارة', 'icon': 'carpenter'},
            
            # نقل وتوصيل
            {'name': 'Livraison', 'name_ar': 'خدمة التوصيل', 'icon': 'delivery_dining'},
            {'name': 'Déménagement', 'name_ar': 'نقل أثاث', 'icon': 'local_shipping'},
            {'name': 'Chauffeur Privé', 'name_ar': 'سائق خاص', 'icon': 'drive_eta'},
            {'name': 'Transport Aéroport', 'name_ar': 'توصيل مطار', 'icon': 'flight'},
            
            # طعام وضيافة
            {'name': 'Traiteur', 'name_ar': 'طبخ مناسبات', 'icon': 'restaurant'},
            {'name': 'Cuisine Quotidienne', 'name_ar': 'طبخ يومي', 'icon': 'restaurant'},
            {'name': 'Pâtisserie Traditionnelle', 'name_ar': 'حلويات تقليدية', 'icon': 'cake'},
            {'name': 'Service Événements', 'name_ar': 'خدمة مناسبات', 'icon': 'celebration'},
            
            # تعليم وتدريب
            {'name': 'Cours Particuliers', 'name_ar': 'دروس خصوصية', 'icon': 'school'},
            {'name': 'Formation Informatique', 'name_ar': 'تعليم حاسوب', 'icon': 'computer'},
            {'name': 'Auto-école', 'name_ar': 'تعليم قيادة', 'icon': 'drive_eta'},
            {'name': 'Formation Artisanale', 'name_ar': 'تعليم حرف', 'icon': 'handyman'},
            
            # جمال وعناية
            {'name': 'Coiffure à Domicile', 'name_ar': 'حلاقة منزلية', 'icon': 'content_cut'},
            {'name': 'Maquillage', 'name_ar': 'خدمة مكياج', 'icon': 'face'},
            {'name': 'Manucure', 'name_ar': 'عناية أظافر', 'icon': 'spa'},
            {'name': 'Service Mariée', 'name_ar': 'خدمة عروس', 'icon': 'face'},
            
            # خدمات تقنية
            {'name': 'Photographie', 'name_ar': 'تصوير مناسبات', 'icon': 'photo_camera'},
            {'name': 'Montage Vidéo', 'name_ar': 'مونتاج فيديو', 'icon': 'video_call'},
            {'name': 'Création Sites Web', 'name_ar': 'إنشاء مواقع', 'icon': 'web'},
            {'name': 'Support Informatique', 'name_ar': 'دعم تقني', 'icon': 'support'},
        ]

        for i, cat_data in enumerate(categories):
            ServiceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'name_ar': cat_data['name_ar'],
                    'icon': cat_data['icon'],
                    'order': i + 1
                }
            )

    def create_areas(self):
        # جميع المناطق المعروفة في نواكشوط
        areas = [
            {'name': 'Tevragh Zeina', 'name_ar': 'تفرغ زينة'},
            {'name': 'Ain Al-Talh', 'name_ar': 'عين الطلح'},
            {'name': 'Riad', 'name_ar': 'الرياض'},
            {'name': 'Arafat', 'name_ar': 'عرفات'},
            {'name': 'Dar Naim', 'name_ar': 'دار النعيم'},
            {'name': 'Tojounin', 'name_ar': 'توجونين'},
            {'name': 'Leksar', 'name_ar': 'لكصار'},
            {'name': 'Sixième', 'name_ar': 'السادسة'},
            {'name': 'Socogim', 'name_ar': 'سوك جيم'},
            {'name': 'Hay Saken', 'name_ar': 'حي ساكن'},
            {'name': 'Tarhil', 'name_ar': 'ترحيل'},
            {'name': 'Carrefour', 'name_ar': 'كارفور'},
            {'name': 'Bouhdida', 'name_ar': 'بوحديدة'},
        ]

        for i, area_data in enumerate(areas):
            NouakchottArea.objects.get_or_create(
                name=area_data['name'],
                defaults={
                    'name_ar': area_data['name_ar'],
                    'area_type': 'district',
                    'order': i + 1
                }
            )