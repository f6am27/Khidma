from django.db import migrations

def fix_empty_emails(apps, schema_editor):
    """
    إصلاح الـ emails الفارغة - إعطاء كل client/worker email وهمي فريد
    لن يحذف أي بيانات - فقط تعديل email
    """
    User = apps.get_model('users', 'User')
    
    # جلب المستخدمين الذين email فارغ (ليسوا admin)
    users_without_email = User.objects.filter(
        email__in=['', None]
    ).exclude(role='admin')
    
    print(f"Found {users_without_email.count()} users with empty email")
    
    # إعطاء كل واحد email وهمي فريد
    for user in users_without_email:
        if user.phone:
            user.email = f"noemail_{user.phone}@placeholder.local"
        else:
            user.email = f"noemail_user_{user.id}@placeholder.local"
        user.save()
        print(f"Fixed: {user.first_name} ({user.role}) - new email: {user.email}")

def reverse_fix(apps, schema_editor):
    """
    إذا أردت التراجع - يرجع emails للفارغ
    """
    User = apps.get_model('users', 'User')
    User.objects.filter(
        email__contains='@placeholder.local'
    ).update(email='')

class Migration(migrations.Migration):
    dependencies = [
    ('users', '0010_savedlocation'),
    ]
    operations = [
        migrations.RunPython(fix_empty_emails, reverse_fix),
    ]