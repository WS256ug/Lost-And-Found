from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class SignUpViewTests(TestCase):
    def test_signup_creates_user_and_profile(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "student1",
                "email": "student@example.com",
                "phone_number": "0712345678",
                "identification_number": "STU-2026-001",
                "role": Profile.Role.STUDENT,
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("item_list"))
        user = User.objects.get(username="student1")
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)
        self.assertEqual(user.profile.phone_number, "0712345678")
        self.assertEqual(user.profile.identification_number, "STU-2026-001")

    def test_signup_requires_identification_number(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "student2",
                "email": "student2@example.com",
                "phone_number": "0700000000",
                "role": Profile.Role.STUDENT,
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Identification card or National ID card number")
        self.assertFalse(User.objects.filter(username="student2").exists())


class LoginViewTests(TestCase):
    def test_staff_login_redirects_to_dashboard(self):
        staff_user = User.objects.create_user(
            username="admin1",
            password="StrongPass123",
            is_staff=True,
        )
        Profile.objects.create(user=staff_user, role=Profile.Role.STAFF)

        response = self.client.post(
            reverse("login"),
            {
                "username": "admin1",
                "password": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_regular_login_redirects_to_item_list(self):
        user = User.objects.create_user(
            username="student3",
            password="StrongPass123",
        )
        Profile.objects.create(user=user, role=Profile.Role.STUDENT)

        response = self.client.post(
            reverse("login"),
            {
                "username": "student3",
                "password": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("item_list"))
