from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        OWNER = "OWNER", "Owner"

    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.STUDENT)
    email = models.EmailField("email address", unique=True)
    room_number = models.IntegerField(default=0)
    contact_number = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.username
