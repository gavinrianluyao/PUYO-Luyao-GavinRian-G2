# Generated for SDD alignment - Owner and Student profiles

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_initial_profiles(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    Owner = apps.get_model('accounts', 'Owner')
    Student = apps.get_model('accounts', 'Student')

    for user in CustomUser.objects.all():
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        contact = user.contact_number or ""
        if user.role == "OWNER":
            Owner.objects.get_or_create(
                user=user,
                defaults={"full_name": full_name, "contact_no": contact[:20]},
            )
        else:
            Student.objects.get_or_create(
                user=user,
                defaults={"full_name": full_name, "contact_no": contact[:20]},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_customuser_contact_number_alter_customuser_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(max_length=100, unique=True, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='room_number',
            field=models.IntegerField(default=0, help_text='Deprecated: use Room/Tenancy instead'),
        ),
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='owner_profile', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('full_name', models.CharField(max_length=100)),
                ('contact_no', models.CharField(max_length=20)),
            ],
            options={
                'verbose_name': 'Owner Profile',
                'verbose_name_plural': 'Owner Profiles',
                'db_table': 'accounts_owner',
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='student_profile', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('full_name', models.CharField(max_length=100)),
                ('contact_no', models.CharField(max_length=20)),
                ('school_id', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('course_year', models.CharField(blank=True, max_length=50, null=True)),
                ('guardian_contact', models.CharField(blank=True, max_length=20, null=True)),
            ],
            options={
                'verbose_name': 'Student Profile',
                'verbose_name_plural': 'Student Profiles',
                'db_table': 'accounts_student',
            },
        ),
        migrations.RunPython(create_initial_profiles, reverse_code=migrations.RunPython.noop),
    ]
