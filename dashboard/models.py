from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser, Owner, Student


class BoardingHouse(models.Model):
    house_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="boarding_houses",
    )
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    house_rules = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_boarding_house"
        verbose_name = "Boarding House"
        verbose_name_plural = "Boarding Houses"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_rooms(self):
        return self.rooms.count()

    @property
    def available_rooms(self):
        return self.rooms.filter(status=Room.Status.AVAILABLE)

    @property
    def occupied_rooms(self):
        return self.rooms.filter(status=Room.Status.OCCUPIED)


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        MAINTENANCE = "MAINTENANCE", "Under Maintenance"

    room_id = models.AutoField(primary_key=True)
    house = models.ForeignKey(
        BoardingHouse,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    room_number = models.CharField(max_length=10)
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Maximum number of tenants",
    )
    monthly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Default monthly rent for the room",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.AVAILABLE,
        help_text="Current availability of the room",
    )

    class Meta:
        db_table = "dashboard_room"
        verbose_name = "Room"
        verbose_name_plural = "Rooms"
        ordering = ["house", "room_number"]
        constraints = [
            # BR-011: room number unique within house
            models.UniqueConstraint(
                fields=["house", "room_number"],
                name="unique_room_number_per_house",
            ),
            # BR-012: capacity > 0
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="room_capacity_gt_zero",
            ),
            # BR-012: monthly_rate >= 0
            models.CheckConstraint(
                condition=models.Q(monthly_rate__gte=0),
                name="room_monthly_rate_gte_zero",
            ),
        ]

    def __str__(self):
        return f"{self.house.name} - Room {self.room_number}"

    @property
    def active_tenants_count(self):
        return self.tenancies.filter(status=Tenancy.Status.ACTIVE).count()

    @property
    def available_slots(self):
        return max(0, self.capacity - self.active_tenants_count)

    def update_occupancy_status(self, save=True):
        """
        BR-015: When a room reaches its capacity, its status changes to Occupied.
        When tenants < capacity and not under maintenance, status returns to Available.
        """
        if self.status == self.Status.MAINTENANCE:
            return
        if self.active_tenants_count >= self.capacity:
            self.status = self.Status.OCCUPIED
        else:
            self.status = self.Status.AVAILABLE
        if save:
            self.save(update_fields=["status"])


class Tenancy(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    tenancy_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="tenancies",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="tenancies",
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Rent agreed at the time of assignment",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        db_table = "dashboard_tenancy"
        verbose_name = "Tenancy"
        verbose_name_plural = "Tenancies"
        ordering = ["-start_date"]
        constraints = [
            # BR-019: end_date >= start_date (when end_date is set)
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="tenancy_end_date_gte_start_date",
            ),
            # BR-018: monthly_rent >= 0
            models.CheckConstraint(
                condition=models.Q(monthly_rent__gte=0),
                name="tenancy_monthly_rent_gte_zero",
            ),
        ]

    def clean(self):
        super().clean()

        # BR-019: The end date of a tenancy cannot be earlier than its start date.
        if (
            self.end_date
            and self.start_date
            and self.end_date < self.start_date
        ):
            raise ValidationError(
                {
                    "end_date": "The end date of a tenancy cannot be earlier than its start date."
                }
            )

        # Validations for ACTIVE tenancy
        if self.status == self.Status.ACTIVE:
            # BR-016: Only a student with a STUDENT profile can be assigned to a room.
            if hasattr(self, "student") and self.student:
                if self.student.user.role != CustomUser.Role.STUDENT:
                    raise ValidationError(
                        {
                            "student": "Only a student with a STUDENT profile can be assigned to a room."
                        }
                    )

            # BR-017: A student can have only one active tenancy at a time.
            if hasattr(self, "student") and self.student:
                active_qs = Tenancy.objects.filter(
                    student=self.student, status=self.Status.ACTIVE
                )
                if self.pk:
                    active_qs = active_qs.exclude(pk=self.pk)
                if active_qs.exists():
                    raise ValidationError(
                        {"student": "This student already has an active tenancy."}
                    )

            # Room availability and capacity checks for new tenancy or room reassignment
            if hasattr(self, "room") and self.room:
                if not self.pk or (
                    self.pk
                    and Tenancy.objects.filter(
                        pk=self.pk, room=self.room
                    ).count()
                    == 0
                ):
                    # BR-013: A room can be assigned to a student only if its status is Available.
                    if self.room.status != Room.Status.AVAILABLE:
                        raise ValidationError(
                            {
                                "room": f"Room {self.room.room_number} is not Available (current status: {self.room.get_status_display()})."
                            }
                        )

                    # BR-014: A room cannot hold more active tenants than its capacity.
                    current_active = self.room.active_tenants_count
                    if current_active >= self.room.capacity:
                        raise ValidationError(
                            {
                                "room": f"Room {self.room.room_number} cannot hold more active tenants than its capacity ({self.room.capacity})."
                            }
                        )

    def save(self, *args, **kwargs):
        # Auto-fill monthly_rent from room's rate if not set (BR-018)
        if (
            self.monthly_rent is None or self.monthly_rent == ""
        ) and hasattr(self, "room") and self.room:
            self.monthly_rent = self.room.monthly_rate
        self.full_clean()
        super().save(*args, **kwargs)
        # BR-015: When a room reaches its capacity, its status changes to Occupied.
        if hasattr(self, "room") and self.room:
            self.room.update_occupancy_status(save=True)

    def end_tenancy(self, end_date=None):
        """
        BR-020: Ending a tenancy sets its end date and its status to Ended.
        The tenancy's bills and payments stay in the records.
        """
        self.status = self.Status.ENDED
        self.end_date = end_date or timezone.now().date()
        if self.end_date < self.start_date:
            self.end_date = self.start_date
        self.save()
        if hasattr(self, "room") and self.room:
            self.room.update_occupancy_status(save=True)

    def __str__(self):
        return f"{self.student} in {self.room} ({self.get_status_display()})"



class Bill(models.Model):
    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIAL = "PARTIAL", "Partially Paid"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"
        VOID = "VOID", "Void"

    bill_id = models.AutoField(primary_key=True)
    tenancy = models.ForeignKey(
        Tenancy,
        on_delete=models.CASCADE,
        related_name="bills",
    )
    created_by = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="issued_bills",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.UNPAID,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_bill"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-due_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="bill_period_end_gte_start",
            ),
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F("period_start")),
                name="bill_due_date_gte_start",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="bill_total_amount_gte_zero",
            ),
            models.UniqueConstraint(
                fields=["tenancy", "period_start", "period_end"],
                name="unique_tenancy_billing_period",
            ),
        ]

    def __str__(self):
        return f"Bill #{self.bill_id} - {self.tenancy.student.full_name} ({self.period_start} to {self.period_end})"

    @property
    def total_payments(self):
        total = sum(p.amount_paid for p in self.payments.all())
        return total if total else Decimal("0.00")

    @property
    def balance_remaining(self):
        return max(Decimal("0.00"), self.total_amount - self.total_payments)

    @property
    def can_edit(self):
        """BR-028: A bill can be edited only while it is not fully paid and not void."""
        return self.status not in [self.Status.PAID, self.Status.VOID]

    def update_status(self, save=True):
        """
        BR-034: Unpaid, Partially Paid, Paid, Overdue, or Void.
        BR-035: Paid when payments equal total, Partially Paid when payments > 0, Unpaid when 0.
        BR-036: An Unpaid or Partially Paid bill becomes Overdue once its due date has passed.
        """
        if self.status == self.Status.VOID:
            return

        today = timezone.now().date()
        total_paid = self.total_payments

        if self.total_amount > 0 and total_paid >= self.total_amount:
            self.status = self.Status.PAID
        elif total_paid > 0:
            if self.due_date < today:
                self.status = self.Status.OVERDUE
            else:
                self.status = self.Status.PARTIAL
        else:
            if self.due_date < today:
                self.status = self.Status.OVERDUE
            else:
                self.status = self.Status.UNPAID

        if save:
            self.save(update_fields=["status", "updated_at"])

    def update_total_amount(self, save=True):
        """BR-026: The total amount of a bill equals the sum of its bill items."""
        total = sum(item.amount for item in self.items.all())
        self.total_amount = total if total else Decimal("0.00")
        self.update_status(save=False)
        if save:
            self.save(update_fields=["total_amount", "status", "updated_at"])

    def void_bill(self):
        """BR-029: Bills are never hard-deleted. A mistaken bill is marked Void by the Owner."""
        self.status = self.Status.VOID
        self.save(update_fields=["status", "updated_at"])

    def clean(self):
        super().clean()
        # BR-024: The due date of a bill cannot be earlier than the start of its billing period.
        if (
            self.due_date
            and self.period_start
            and self.due_date < self.period_start
        ):
            raise ValidationError(
                {
                    "due_date": "The due date cannot be earlier than the start of the billing period."
                }
            )
        if (
            self.period_end
            and self.period_start
            and self.period_end < self.period_start
        ):
            raise ValidationError(
                {
                    "period_end": "The billing period end date cannot be earlier than its start date."
                }
            )
        # BR-027: A tenancy cannot have two bills for the same billing period.
        if self.tenancy_id and self.period_start and self.period_end:
            existing = Bill.objects.filter(
                tenancy=self.tenancy,
                period_start=self.period_start,
                period_end=self.period_end,
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            existing = existing.exclude(status=self.Status.VOID)
            if existing.exists():
                raise ValidationError(
                    "A bill already exists for this tenancy during this billing period (BR-027). Add additional charges as bill items instead."
                )


class BillItem(models.Model):
    class ChargeType(models.TextChoices):
        RENT = "RENT", "Rent"
        ELECTRIC = "ELECTRIC", "Electricity"
        WATER = "WATER", "Water"
        OTHER = "OTHER", "Other"

    item_id = models.AutoField(primary_key=True)
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="items",
    )
    charge_type = models.CharField(
        max_length=10,
        choices=ChargeType.choices,
    )
    description = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        db_table = "dashboard_bill_item"
        verbose_name = "Bill Item"
        verbose_name_plural = "Bill Items"
        ordering = ["item_id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="bill_item_amount_gt_zero",
            ),
        ]

    def __str__(self):
        return f"{self.get_charge_type_display()} - ₱{self.amount}"

    def clean(self):
        super().clean()
        # BR-025: amount must be greater than 0
        if self.amount is not None and self.amount <= 0:
            raise ValidationError(
                {"amount": "Bill item amount must be greater than 0."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if hasattr(self, "bill") and self.bill:
            self.bill.update_total_amount(save=True)

    def delete(self, *args, **kwargs):
        bill = self.bill
        super().delete(*args, **kwargs)
        if bill:
            bill.update_total_amount(save=True)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        GCASH = "GCASH", "GCash"
        BANK = "BANK", "Bank Transfer"
        OTHER = "OTHER", "Other"

    payment_id = models.AutoField(primary_key=True)
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    recorded_by = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="recorded_payments",
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_date = models.DateField(default=timezone.now)
    method = models.CharField(
        max_length=10,
        choices=Method.choices,
    )
    remarks = models.CharField(max_length=255, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-payment_date", "-recorded_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_paid__gt=0),
                name="payment_amount_gt_zero",
            ),
        ]

    def __str__(self):
        return f"Payment #{self.payment_id}: ₱{self.amount_paid} for Bill #{self.bill_id}"

    def clean(self):
        super().clean()
        if self.amount_paid is not None and self.amount_paid <= 0:
            raise ValidationError(
                {"amount_paid": "Payment amount must be greater than 0."}
            )

        if hasattr(self, "bill") and self.bill:
            if self.bill.status == Bill.Status.VOID:
                raise ValidationError("Cannot record payment for a Void bill.")

            current_payments = self.bill.total_payments
            if self.pk:
                current_payments -= Payment.objects.get(pk=self.pk).amount_paid

            # BR-033: Total payments on a bill cannot exceed the bill's total amount
            if (current_payments + self.amount_paid) > self.bill.total_amount:
                max_allowed = self.bill.total_amount - current_payments
                raise ValidationError(
                    {
                        "amount_paid": f"Total payments cannot exceed bill total amount (₱{self.bill.total_amount}). Maximum payable is ₱{max_allowed}."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if hasattr(self, "bill") and self.bill:
            self.bill.update_status(save=True)

    def delete(self, *args, **kwargs):
        bill = self.bill
        super().delete(*args, **kwargs)
        if bill:
            bill.update_status(save=True)


class Notification(models.Model):
    class Type(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming Due Date"
        OVERDUE = "OVERDUE", "Overdue Payment"

    notification_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
    )
    message = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "dashboard_notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-scheduled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bill", "type"],
                name="unique_bill_notification_type",
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} for {self.student}: {self.message}"


def check_and_create_bill_reminders(bill):
    """
    BR-039: The system creates an Upcoming reminder a set number of days before a bill's due date (e.g. 3 days).
    BR-040: The system creates an Overdue reminder when a bill passes its due date without being fully paid.
    BR-041: A bill that is fully paid or Void generates no further reminders.
    BR-042: A reminder is sent only to the student on that bill's tenancy.
    """
    if bill.status in [Bill.Status.PAID, Bill.Status.VOID]:
        return

    today = timezone.now().date()
    student = bill.tenancy.student

    # Upcoming reminder: within 3 days of due date
    if today <= bill.due_date and (bill.due_date - today).days <= 3:
        Notification.objects.get_or_create(
            bill=bill,
            type=Notification.Type.UPCOMING,
            defaults={
                "student": student,
                "message": f"Reminder: Your bill for {bill.tenancy.room} of ₱{bill.balance_remaining} is due on {bill.due_date}.",
                "scheduled_at": timezone.now(),
            },
        )

    # Overdue reminder: past due date and not fully paid
    if today > bill.due_date and bill.balance_remaining > 0:
        Notification.objects.get_or_create(
            bill=bill,
            type=Notification.Type.OVERDUE,
            defaults={
                "student": student,
                "message": f"URGENT: Your bill for {bill.tenancy.room} of ₱{bill.balance_remaining} was due on {bill.due_date} and is now overdue.",
                "scheduled_at": timezone.now(),
            },
        )
