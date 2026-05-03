from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import Item


class ItemViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff1", password="StrongPass123")
        self.staff_user = User.objects.create_user(
            username="admin1",
            password="StrongPass123",
            is_staff=True,
        )
        Profile.objects.create(user=self.staff_user, role=Profile.Role.STAFF)
        self.item = Item.objects.create(
            report_type=Item.ReportType.LOST,
            title="Lost Laptop",
            description="Black Dell laptop",
            category=Item.Category.ELECTRONICS,
            location="Library",
            event_date="2026-04-28",
            status=Item.Status.LOST,
            reported_by=self.user,
        )

    def test_item_list_page_loads(self):
        response = self.client.get(reverse("item_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lost Laptop")

    def test_report_lost_item_requires_login(self):
        response = self.client.get(reverse("report_lost_item"))

        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_loads_for_staff(self):
        self.client.login(username="admin1", password="StrongPass123")

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")

    def test_admin_dashboard_redirects_non_staff_user(self):
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(response, reverse("item_list"))

    def test_admin_item_edit_updates_item_status(self):
        self.client.login(username="admin1", password="StrongPass123")

        response = self.client.post(
            reverse("admin_item_edit", args=[self.item.pk]),
            {
                "report_type": Item.ReportType.LOST,
                "title": self.item.title,
                "description": self.item.description,
                "category": self.item.category,
                "location": self.item.location,
                "event_date": "2026-04-28",
                "status": Item.Status.CLAIMED,
                "reported_by": self.user.pk,
            },
        )

        self.assertRedirects(response, reverse("admin_item_list"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.Status.CLAIMED)
