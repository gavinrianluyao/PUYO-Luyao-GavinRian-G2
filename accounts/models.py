from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        OWNER = "OWNER", "Owner"

    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.STUDENT
    )
    email = models.EmailField("email address", max_length=100, unique=True)
    room_number = models.IntegerField(
        default=0, help_text="Deprecated: use Room/Tenancy instead"
    )
    contact_number = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.username

    @property
    def assigned_room_number(self):
        active = self.get_active_tenancy()
        if active and active.room:
            return active.room.room_number
        return None

    def get_active_tenancy(self):
        if self.role == self.Role.STUDENT and hasattr(self, "student_profile"):
            return (
                self.student_profile.tenancies.filter(status="ACTIVE")
                .select_related("room", "room__house")
                .first()
            )
        return None


class Owner(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="owner_profile",
    )
    full_name = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=20)

    class Meta:
        db_table = "accounts_owner"
        verbose_name = "Owner Profile"
        verbose_name_plural = "Owner Profiles"

    def __str__(self):
        return self.full_name or self.user.username


class Student(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="student_profile",
    )
    full_name = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=20)
    school_id = models.CharField(
        max_length=20, unique=True, null=True, blank=True
    )
    course_year = models.CharField(max_length=50, null=True, blank=True)
    guardian_contact = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "accounts_student"
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def __str__(self):
        return self.full_name or self.user.username

    def get_active_tenancy(self):
        return (
            self.tenancies.filter(status="ACTIVE")
            .select_related("room", "room__house")
            .first()
        )


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every user account has exactly one matching profile record
    (BR-003, BR-004).
    """
    full_name = instance.get_full_name() or instance.username
    contact = instance.contact_number or ""
    if instance.role == CustomUser.Role.OWNER:
        Owner.objects.get_or_create(
            user=instance,
            defaults={"full_name": full_name, "contact_no": contact[:20]},
        )
    elif instance.role == CustomUser.Role.STUDENT:
        Student.objects.get_or_create(
            user=instance,
            defaults={"full_name": full_name, "contact_no": contact[:20]},
        )
