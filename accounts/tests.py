from django.test import TestCase
from django.urls import reverse

from .models import CustomUser, Student


class SignUpViewTests(TestCase):
    def test_registration_creates_hashed_student_and_shows_success_message(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newstudent",
                "email": "newstudent@example.com",
                "password1": "PuyoStrongPass!2468",
                "password2": "PuyoStrongPass!2468",
            },
            follow=True,
        )

        self.assertContains(
            response, "Your account has been created. You can now log in."
        )
        user = CustomUser.objects.get(username="newstudent")
        self.assertEqual(user.role, CustomUser.Role.STUDENT)
        self.assertTrue(user.check_password("PuyoStrongPass!2468"))
        self.assertTrue(Student.objects.filter(user=user).exists())
