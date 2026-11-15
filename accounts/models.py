from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        OWNER = "OWNER", "Owner"

    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.STUDENT)
    room_number = models.IntegerField(
        default=0
    )

    def __str__(self):
        return self.username

