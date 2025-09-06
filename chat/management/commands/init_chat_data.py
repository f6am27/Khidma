# chat/management/commands/init_chat_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import Profile
from chat.models import Conversation, Message, BlockedUser, Report


class Command(BaseCommand):
    """
    أمر تهيئة البيانات الوهمية للمحادثات
    Initialize chat dummy data command
    """
    help = 'Initialise les données de démonstration pour le système de chat'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprimer toutes les données de chat existantes avant l\'initialisation',
        )
        parser.add_argument(
            '--conversations',
            type=int,
            default=5,
            help='Nombre de conversations à créer (défaut: 5)',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('🗑️  Suppression des données de chat existantes...')
            self.clear_chat_data()
        
        self.stdout.write('🚀 Initialisation des données de chat...')
        
        # التحقق من وجود المستخدمين
        if not self.check_users():
            return
        
        # إنشاء المحادثات
        conversations = self.create_conversations(options['conversations'])
        
        # إنشاء الرسائل
        self.create_messages(conversations)
        
        # إنشاء المستخدمين المحظورين
        self.create_blocked_users()
        
        # إنشاء التبليغات
        self.create_reports()
        
        self.stdout.write(
            self.style.SUCCESS('✅ تم تهيئة بيانات المحادثات بنجاح!')
        )
        
        # عرض الإحصائيات
        self.display_statistics()
    
    def clear_chat_data(self):
        """حذف جميع بيانات المحادثات"""
        Report.objects.all().delete()
        BlockedUser.objects.all().delete()
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('تم حذف جميع بيانات المحادثات'))
    
    def check_users(self):
        """التحقق من وجود المستخدمين المطلوبين"""
        required_profiles = 4  # حد أدنى للعمل
        profile_count = Profile.objects.count()
        
        if profile_count < required_profiles:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ يجب وجود على الأقل {required_profiles} مستخدمين في النظام. '
                    f'الموجود حالياً: {profile_count}'
                )
            )
            self.stdout.write('💡 قم بتشغيل أوامر تهيئة التطبيقات الأخرى أولاً')
            return False
        
        return True
    
    def create_conversations(self, max_conversations=5):
        """إنشاء المحادثات"""
        self.stdout.write('💬 إنشاء المحادثات...')
        
        # الحصول على العملاء والعمال
        clients = list(Profile.objects.filter(role='client'))
        workers = list(Profile.objects.filter(role='worker'))
        
        # التحقق من توفر العدد الكافي
        if len(clients) == 0 or len(workers) == 0:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ يجب وجود عميل واحد وعامل واحد على الأقل. '
                    f'العملاء: {len(clients)}, العمال: {len(workers)}'
                )
            )
            return []
        
        conversations = []
        
        # إنشاء محادثات حسب العدد المتوفر
        available_conversations = min(len(clients), len(workers), max_conversations)
        
        self.stdout.write(f'  📊 سيتم إنشاء {available_conversations} محادثة من أصل {max_conversations} محادثة مطلوبة')
        
        for i in range(available_conversations):
            # توزيع دوري للمستخدمين
            client = clients[i % len(clients)]
            worker = workers[i % len(workers)]
            
            # تجنب إنشاء محادثة بين نفس المستخدمين مرتين
            if Conversation.objects.filter(client=client, worker=worker).exists():
                continue
                
            conversation_data = {
                'client': client,
                'worker': worker,
                'is_active': True if i < available_conversations - 1 else False,  # آخر محادثة غير نشطة
                'created_at': timezone.now() - timezone.timedelta(days=i+1),
            }
            
            conversation, created = Conversation.objects.get_or_create(
                client=conversation_data['client'],
                worker=conversation_data['worker'],
                defaults={
                    'is_active': conversation_data['is_active'],
                    'created_at': conversation_data['created_at'],
                    'updated_at': conversation_data['created_at'],
                }
            )
            
            if created:
                conversations.append(conversation)
                status = "نشطة" if conversation.is_active else "غير نشطة"
                self.stdout.write(f'  ✓ محادثة {status} بين {conversation.client.user.username} و {conversation.worker.user.username}')
        
        return conversations
    
    def create_messages(self, conversations):
        """إنشاء الرسائل"""
        if not conversations:
            self.stdout.write('⚠️  لا توجد محادثات لإنشاء رسائل')
            return
            
        self.stdout.write('💌 إنشاء الرسائل...')
        
        # قوالب رسائل متنوعة
        message_templates = [
            {
                'client_messages': [
                    "Bonjour, j'ai besoin d'aide pour réparer ma plomberie.",
                    "Il y a une fuite sous l'évier de la cuisine.",
                    "Parfait ! Voici mon adresse : 123 Rue de la Paix, Nouakchott",
                    "Bonjour, êtes-vous en route ?"
                ],
                'worker_messages': [
                    "Bonjour ! Je peux vous aider. Quel est le problème exactement ?",
                    "D'accord, je peux venir aujourd'hui vers 14h. Ça vous convient ?",
                    "Merci ! Je serai là à 14h précises.",
                    "Oui, j'arrive dans 10 minutes !"
                ]
            },
            {
                'client_messages': [
                    "Salut ! Tu peux me nettoyer ma maison demain ?",
                    "C'est un appartement de 80m², 3 chambres.",
                    "D'accord, c'est confirmé !"
                ],
                'worker_messages': [
                    "Bonjour ! Bien sûr, quelle surface approximativement ?",
                    "Perfect ! Je peux venir vers 9h du matin. Le prix sera 5000 MRU."
                ]
            },
            {
                'client_messages': [
                    "Bonjour, j'ai besoin de vos services.",
                    "Merci pour votre réponse rapide."
                ],
                'worker_messages': [
                    "Bonjour ! Je peux vous aider. De quoi avez-vous besoin ?",
                    "Je suis disponible pour vous aider."
                ]
            }
        ]
        
        # إنشاء رسائل لكل محادثة
        for i, conv in enumerate(conversations):
            template_index = i % len(message_templates)
            template = message_templates[template_index]
            
            client_msgs = template['client_messages']
            worker_msgs = template['worker_messages']
            
            # إنشاء رسائل متناوبة بين العميل والعامل
            max_messages = min(len(client_msgs), len(worker_msgs))
            
            for j in range(max_messages):
                # رسالة من العميل
                if j < len(client_msgs):
                    Message.objects.create(
                        conversation=conv,
                        sender=conv.client,
                        content=client_msgs[j],
                        created_at=conv.created_at + timezone.timedelta(minutes=5 + j*10),
                        updated_at=conv.created_at + timezone.timedelta(minutes=5 + j*10),
                        is_read=True,
                        read_at=conv.created_at + timezone.timedelta(minutes=7 + j*10)
                    )
                
                # رسالة من العامل
                if j < len(worker_msgs):
                    is_last_message = (j == max_messages - 1) and (i == 0)  # آخر رسالة في أول محادثة تبقى غير مقروءة
                    Message.objects.create(
                        conversation=conv,
                        sender=conv.worker,
                        content=worker_msgs[j],
                        created_at=conv.created_at + timezone.timedelta(minutes=8 + j*10),
                        updated_at=conv.created_at + timezone.timedelta(minutes=8 + j*10),
                        is_read=not is_last_message,
                        read_at=None if is_last_message else conv.created_at + timezone.timedelta(minutes=10 + j*10)
                    )
        
        self.stdout.write('  ✓ تم إنشاء الرسائل لجميع المحادثات')
    
    def create_blocked_users(self):
        """إنشاء المستخدمين المحظورين"""
        self.stdout.write('🚫 إنشاء المستخدمين المحظورين...')
        
        profiles = list(Profile.objects.all())
        
        if len(profiles) < 4:
            self.stdout.write('⚠️  عدد المستخدمين غير كافي لإنشاء حظر')
            return
        
        # إنشاء 2-3 حالات حظر كحد أقصى للبيانات الوهمية
        max_blocks = min(3, len(profiles) // 2)
        
        for i in range(max_blocks):
            blocker = profiles[i]
            blocked = profiles[-(i+1)]  # من النهاية
            
            if blocker != blocked:  # تأكد من عدم حظر النفس
                blocked_user, created = BlockedUser.objects.get_or_create(
                    blocker=blocker,
                    blocked=blocked,
                    defaults={
                        'reason': f"Comportement inapproprié #{i+1}",
                        'created_at': timezone.now() - timezone.timedelta(days=i+1),
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ حظر {blocked_user.blocked.user.username} بواسطة {blocked_user.blocker.user.username}')
    
    def create_reports(self):
        """إنشاء التبليغات"""
        self.stdout.write('📢 إنشاء التبليغات...')
        
        profiles = list(Profile.objects.all())
        conversations = list(Conversation.objects.all())
        
        if len(profiles) < 4:
            self.stdout.write('⚠️  عدد المستخدمين غير كافي لإنشاء تبليغات')
            return
        
        report_reasons = ['harassment', 'spam', 'scam_fraud', 'inappropriate_content']
        report_statuses = ['resolved', 'under_review', 'pending']
        
        # إنشاء 2-4 تبليغات كحد أقصى للبيانات الوهمية
        max_reports = min(4, len(profiles) // 2)
        
        for i in range(max_reports):
            reporter = profiles[i]
            reported_user = profiles[-(i+1)]  # من النهاية
            
            if reporter != reported_user:  # تأكد من عدم تبليغ النفس
                report, created = Report.objects.get_or_create(
                    reporter=reporter,
                    reported_user=reported_user,
                    conversation=conversations[i % len(conversations)] if conversations else None,
                    reason=report_reasons[i % len(report_reasons)],
                    defaults={
                        'description': f"Description du problème #{i+1}",
                        'status': report_statuses[i % len(report_statuses)],
                        'admin_notes': "Traité par l'administration" if i == 0 else "",
                        'resolved_at': timezone.now() - timezone.timedelta(hours=6) if i == 0 else None,
                        'created_at': timezone.now() - timezone.timedelta(days=i+1),
                        'updated_at': timezone.now() - timezone.timedelta(days=i+1),
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ تبليغ من {report.reporter.user.username} ضد {report.reported_user.user.username}')
    
    def display_statistics(self):
        """عرض إحصائيات البيانات المُنشأة"""
        self.stdout.write('\n📊 إحصائيات البيانات:')
        self.stdout.write(f'  💬 المحادثات: {Conversation.objects.count()}')
        self.stdout.write(f'  💌 الرسائل: {Message.objects.count()}')
        self.stdout.write(f'  🚫 المستخدمين المحظورين: {BlockedUser.objects.count()}')
        self.stdout.write(f'  📢 التبليغات: {Report.objects.count()}')
        
        active_conversations = Conversation.objects.filter(is_active=True).count()
        unread_messages = Message.objects.filter(is_read=False).count()
        pending_reports = Report.objects.filter(status='pending').count()
        
        self.stdout.write(f'  ✅ المحادثات النشطة: {active_conversations}')
        self.stdout.write(f'  📩 الرسائل غير المقروءة: {unread_messages}')
        self.stdout.write(f'  ⏳ التبليغات المعلقة: {pending_reports}')
        
        # إحصائيات المستخدمين
        clients_count = Profile.objects.filter(role='client').count()
        workers_count = Profile.objects.filter(role='worker').count()
        
        self.stdout.write(f'\n👥 المستخدمين المتاحين:')
        self.stdout.write(f'  👤 العملاء: {clients_count}')
        self.stdout.write(f'  🔧 العمال: {workers_count}')
        
        self.stdout.write(f'\n🎉 تطبيق chat جاهز للاستخدام!')
        self.stdout.write('📱 يمكنك الآن اختبار APIs المحادثات')
        self.stdout.write('💡 لإنشاء محادثات أكثر، استخدم: --conversations NUMBER')