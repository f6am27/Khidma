# payments/management/commands/migrate_past_payments.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import ServiceRequest
from payments.models import Payment


class Command(BaseCommand):
    help = 'Migrate past completed tasks to Payment records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually creating payments',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.SUCCESS('Starting migration...'))
        
        # Get all completed tasks that don't have a payment yet
        completed_tasks = ServiceRequest.objects.filter(
            status='completed',
            final_price__isnull=False,
            payment__isnull=True  # Only tasks without payment
        ).select_related('client', 'assigned_worker')
        
        total_count = completed_tasks.count()
        self.stdout.write(f'Found {total_count} tasks to migrate')
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No tasks to migrate'))
            return
        
        created_count = 0
        error_count = 0
        
        for task in completed_tasks:
            try:
                # Validate task has required data
                if not task.client:
                    self.stdout.write(
                        self.style.ERROR(f'Task {task.id}: Missing client')
                    )
                    error_count += 1
                    continue
                
                if not task.assigned_worker:
                    self.stdout.write(
                        self.style.ERROR(f'Task {task.id}: Missing assigned worker')
                    )
                    error_count += 1
                    continue
                
                if task.final_price <= 0:
                    self.stdout.write(
                        self.style.WARNING(f'Task {task.id}: Invalid final price {task.final_price}')
                    )
                    error_count += 1
                    continue
                
                if not dry_run:
                    # Create payment record
                    payment = Payment.objects.create(
                        task=task,
                        payer=task.client,
                        receiver=task.assigned_worker,
                        amount=task.final_price,
                        payment_method='cash',
                        status='completed',
                        completed_at=task.completed_at or timezone.now(),
                        notes=f'Migrated from completed task'
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Task {task.id}: Payment {payment.id} created - {payment.amount} MRU'
                        )
                    )
                    created_count += 1
                else:
                    # Dry run mode - just show what would be created
                    self.stdout.write(
                        f'[DRY RUN] Task {task.id}: Would create payment - {task.final_price} MRU '
                        f'from {task.client.get_full_name() or task.client.phone} '
                        f'to {task.assigned_worker.get_full_name() or task.assigned_worker.phone}'
                    )
                    created_count += 1
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Task {task.id}: Error - {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Migration Summary:'))
        self.stdout.write(self.style.SUCCESS(f'Total tasks processed: {total_count}'))
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {created_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN - no payments were created'))
        else:
            self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))