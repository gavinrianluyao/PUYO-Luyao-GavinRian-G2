# Generated for SDD alignment - Billing, BillItem, Payment, Notification models

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_owner_student'),
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('bill_id', models.AutoField(primary_key=True, serialize=False)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('due_date', models.DateField()),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('status', models.CharField(choices=[('UNPAID', 'Unpaid'), ('PARTIAL', 'Partially Paid'), ('PAID', 'Paid'), ('OVERDUE', 'Overdue'), ('VOID', 'Void')], default='UNPAID', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='issued_bills', to='accounts.owner')),
                ('tenancy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bills', to='dashboard.tenancy')),
            ],
            options={
                'verbose_name': 'Bill',
                'verbose_name_plural': 'Bills',
                'db_table': 'dashboard_bill',
                'ordering': ['-due_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BillItem',
            fields=[
                ('item_id', models.AutoField(primary_key=True, serialize=False)),
                ('charge_type', models.CharField(choices=[('RENT', 'Rent'), ('ELECTRIC', 'Electricity'), ('WATER', 'Water'), ('OTHER', 'Other')], max_length=10)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='dashboard.bill')),
            ],
            options={
                'verbose_name': 'Bill Item',
                'verbose_name_plural': 'Bill Items',
                'db_table': 'dashboard_bill_item',
                'ordering': ['item_id'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('payment_id', models.AutoField(primary_key=True, serialize=False)),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('payment_date', models.DateField(default=django.utils.timezone.now)),
                ('method', models.CharField(choices=[('CASH', 'Cash'), ('GCASH', 'GCash'), ('BANK', 'Bank Transfer'), ('OTHER', 'Other')], max_length=10)),
                ('remarks', models.CharField(blank=True, max_length=255, null=True)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='dashboard.bill')),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recorded_payments', to='accounts.owner')),
            ],
            options={
                'verbose_name': 'Payment',
                'verbose_name_plural': 'Payments',
                'db_table': 'dashboard_payment',
                'ordering': ['-payment_date', '-recorded_at'],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('notification_id', models.AutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('UPCOMING', 'Upcoming Due Date'), ('OVERDUE', 'Overdue Payment')], max_length=10)),
                ('message', models.CharField(max_length=255)),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='dashboard.bill')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='accounts.student')),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'db_table': 'dashboard_notification',
                'ordering': ['-scheduled_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='bill',
            constraint=models.CheckConstraint(condition=models.Q(period_end__gte=models.F('period_start')), name='bill_period_end_gte_start'),
        ),
        migrations.AddConstraint(
            model_name='bill',
            constraint=models.CheckConstraint(condition=models.Q(due_date__gte=models.F('period_start')), name='bill_due_date_gte_start'),
        ),
        migrations.AddConstraint(
            model_name='bill',
            constraint=models.CheckConstraint(condition=models.Q(total_amount__gte=0), name='bill_total_amount_gte_zero'),
        ),
        migrations.AddConstraint(
            model_name='bill',
            constraint=models.UniqueConstraint(fields=('tenancy', 'period_start', 'period_end'), name='unique_tenancy_billing_period'),
        ),
        migrations.AddConstraint(
            model_name='billitem',
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name='bill_item_amount_gt_zero'),
        ),
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.CheckConstraint(condition=models.Q(amount_paid__gt=0), name='payment_amount_gt_zero'),
        ),
        migrations.AddConstraint(
            model_name='notification',
            constraint=models.UniqueConstraint(fields=('bill', 'type'), name='unique_bill_notification_type'),
        ),
    ]
