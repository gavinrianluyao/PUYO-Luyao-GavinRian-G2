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
