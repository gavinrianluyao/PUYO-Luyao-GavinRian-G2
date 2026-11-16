# Generated for SDD alignment - BoardingHouse, Room, Tenancy models

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0003_owner_student'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoardingHouse',
            fields=[
                ('house_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=255)),
                ('house_rules', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='boarding_houses', to='accounts.owner')),
            ],
            options={
                'verbose_name': 'Boarding House',
                'verbose_name_plural': 'Boarding Houses',
                'db_table': 'dashboard_boarding_house',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('room_id', models.AutoField(primary_key=True, serialize=False)),
                ('room_number', models.CharField(max_length=10)),
                ('capacity', models.PositiveIntegerField(help_text='Maximum number of tenants', validators=[django.core.validators.MinValueValidator(1)])),
                ('monthly_rate', models.DecimalField(decimal_places=2, help_text='Default monthly rent for the room', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('OCCUPIED', 'Occupied'), ('MAINTENANCE', 'Under Maintenance')], default='AVAILABLE', help_text='Current availability of the room', max_length=15)),
                ('house', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rooms', to='dashboard.boardinghouse')),
            ],
            options={
                'verbose_name': 'Room',
                'verbose_name_plural': 'Rooms',
                'db_table': 'dashboard_room',
                'ordering': ['house', 'room_number'],
            },
        ),
        migrations.CreateModel(
            name='Tenancy',
            fields=[
                ('tenancy_id', models.AutoField(primary_key=True, serialize=False)),
                ('start_date', models.DateField(default=django.utils.timezone.now)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('monthly_rent', models.DecimalField(decimal_places=2, help_text='Rent agreed at the time of assignment', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('ENDED', 'Ended')], default='ACTIVE', max_length=10)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenancies', to='dashboard.room')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenancies', to='accounts.student')),
            ],
            options={
                'verbose_name': 'Tenancy',
                'verbose_name_plural': 'Tenancies',
                'db_table': 'dashboard_tenancy',
                'ordering': ['-start_date'],
            },
        ),
        migrations.AddConstraint(
            model_name='room',
            constraint=models.UniqueConstraint(fields=('house', 'room_number'), name='unique_room_number_per_house'),
        ),
        migrations.AddConstraint(
            model_name='room',
            constraint=models.CheckConstraint(condition=models.Q(capacity__gt=0), name='room_capacity_gt_zero'),
        ),
        migrations.AddConstraint(
            model_name='room',
            constraint=models.CheckConstraint(condition=models.Q(monthly_rate__gte=0), name='room_monthly_rate_gte_zero'),
        ),
        migrations.AddConstraint(
            model_name='tenancy',
            constraint=models.CheckConstraint(condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F('start_date')), name='tenancy_end_date_gte_start_date'),
        ),
        migrations.AddConstraint(
            model_name='tenancy',
            constraint=models.CheckConstraint(condition=models.Q(monthly_rent__gte=0), name='tenancy_monthly_rent_gte_zero'),
        ),
    ]
