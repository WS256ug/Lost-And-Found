from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import Claim, Conversation, Item, Message


class ItemViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff1",
            email="reporter@example.com",
            password="StrongPass123",
        )
        self.staff_user = User.objects.create_user(
            username="admin1",
            password="StrongPass123",
            is_staff=True,
        )
        Profile.objects.create(
            user=self.user,
            role=Profile.Role.STUDENT,
            phone_number="0712345678",
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
        self.found_item = Item.objects.create(
            report_type=Item.ReportType.FOUND,
            title="Found Phone",
            description="Phone found near the cafeteria",
            category=Item.Category.ELECTRONICS,
            location="Cafeteria",
            event_date="2026-04-29",
            status=Item.Status.FOUND,
            reported_by=self.user,
        )
        self.found_item.verification_question = "What is on the lock screen?"
        self.found_item.set_verification_answer("blue mountain")
        self.found_item.save()

    def create_found_item(self):
        return Item.objects.create(
            report_type=Item.ReportType.FOUND,
            title="Found Phone",
            description="Phone found near the cafeteria",
            category=Item.Category.ELECTRONICS,
            location="Cafeteria",
            event_date="2026-04-29",
            status=Item.Status.FOUND,
            reported_by=self.user,
        )

    def test_item_list_page_loads(self):
        response = self.client.get(reverse("item_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'name="type"')
        self.assertContains(response, 'name="status"')
        self.assertContains(response, 'name="category"')
        self.assertContains(response, "Found item")
        self.assertContains(response, "Posted")
        self.assertNotContains(response, "Found Phone")
        self.assertNotContains(response, "Cafeteria")
        self.assertNotContains(response, "Lost Laptop")

    def test_regular_user_can_search_and_filter_item_list(self):
        viewer = User.objects.create_user(
            username="viewer1",
            password="StrongPass123",
        )
        book = Item.objects.create(
            report_type=Item.ReportType.FOUND,
            title="Found Statistics Book",
            description="Blue statistics textbook.",
            category=Item.Category.BOOKS,
            location="Library second floor",
            event_date="2026-06-15",
            status=Item.Status.FOUND,
            reported_by=self.user,
        )
        self.client.login(username="viewer1", password="StrongPass123")

        response = self.client.get(
            reverse("item_list"),
            {
                "q": "statistics",
                "type": Item.ReportType.FOUND,
                "status": Item.Status.FOUND,
                "category": Item.Category.BOOKS,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item.pk for item in response.context["items"]], [book.pk])
        self.assertContains(response, "Found item")
        self.assertNotContains(response, "Found Statistics Book")
        self.assertNotContains(response, "Library second floor")

    def test_report_lost_item_requires_login(self):
        response = self.client.get(reverse("report_lost_item"))

        self.assertEqual(response.status_code, 302)

    def test_item_detail_loads_for_reporting_user(self):
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.get(reverse("item_detail", args=[self.item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("item_edit", args=[self.item.pk]))
        self.assertContains(response, reverse("item_delete", args=[self.item.pk]))

    def test_item_detail_shows_message_reporter_for_other_user(self):
        User.objects.create_user(username="other1", password="StrongPass123")
        self.client.login(username="other1", password="StrongPass123")

        response = self.client.get(reverse("item_detail", args=[self.found_item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("submit_claim", args=[self.found_item.pk]))
        self.assertContains(response, "Found item")
        self.assertNotContains(response, "Found Phone")
        self.assertNotContains(response, "Cafeteria")
        self.assertNotContains(response, "Message reporter")

    def test_item_image_serves_database_image_for_found_item(self):
        self.found_item.image_data = b"image-bytes"
        self.found_item.image_content_type = "image/png"
        self.found_item.image_filename = "found.png"
        self.found_item.save(
            update_fields=["image_data", "image_content_type", "image_filename"]
        )

        response = self.client.get(reverse("item_image", args=[self.found_item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, b"image-bytes")

    def test_item_image_blocks_private_lost_item_for_uninvolved_user(self):
        self.item.image_data = b"private-image"
        self.item.image_content_type = "image/png"
        self.item.save(update_fields=["image_data", "image_content_type"])
        User.objects.create_user(username="other1", password="StrongPass123")
        self.client.login(username="other1", password="StrongPass123")

        response = self.client.get(reverse("item_image", args=[self.item.pk]))

        self.assertEqual(response.status_code, 404)

    def test_start_conversation_is_blocked_for_protected_found_item(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        self.client.login(username="participant1", password="StrongPass123")

        response = self.client.post(reverse("start_conversation", args=[self.found_item.pk]))

        self.assertRedirects(response, reverse("item_detail", args=[self.found_item.pk]))
        self.assertFalse(Conversation.objects.filter(item=self.found_item, participant=participant).exists())

    def test_claimant_can_message_reporter_for_protected_found_item(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        Claim.objects.create(
            item=self.found_item,
            claimant=participant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.client.login(username="participant1", password="StrongPass123")

        detail_response = self.client.get(
            reverse("item_detail", args=[self.found_item.pk])
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Found Phone")
        self.assertContains(detail_response, "Cafeteria")
        self.assertContains(detail_response, "Message reporter")

        response = self.client.post(
            reverse("start_conversation", args=[self.found_item.pk])
        )
        conversation = Conversation.objects.get(
            item=self.found_item,
            participant=participant,
        )

        self.assertRedirects(
            response,
            reverse("conversation_detail", args=[conversation.pk]),
        )

    def test_start_conversation_reuses_existing_chat(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        conversation = Conversation.objects.create(item=self.found_item, participant=participant)
        self.client.login(username="participant1", password="StrongPass123")

        response = self.client.post(reverse("start_conversation", args=[self.found_item.pk]))

        self.assertRedirects(response, reverse("conversation_detail", args=[conversation.pk]))
        self.assertEqual(
            Conversation.objects.filter(item=self.found_item, participant=participant).count(),
            1,
        )

    def test_reporter_cannot_start_chat_with_self(self):
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.post(reverse("start_conversation", args=[self.item.pk]))

        self.assertRedirects(response, reverse("conversation_list"))
        self.assertFalse(Conversation.objects.exists())

    def test_participant_can_send_message(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        conversation = Conversation.objects.create(item=self.item, participant=participant)
        self.client.login(username="participant1", password="StrongPass123")

        response = self.client.post(
            reverse("conversation_detail", args=[conversation.pk]),
            {"body": "Hi, I think this may be mine."},
        )

        self.assertRedirects(response, reverse("conversation_detail", args=[conversation.pk]))
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.sender, participant)
        self.assertEqual(message.body, "Hi, I think this may be mine.")

    def test_reporter_can_reply_to_message(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        conversation = Conversation.objects.create(item=self.item, participant=participant)
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.post(
            reverse("conversation_detail", args=[conversation.pk]),
            {"body": "Please describe the laptop sticker."},
        )

        self.assertRedirects(response, reverse("conversation_detail", args=[conversation.pk]))
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.sender, self.user)

    def test_unrelated_user_cannot_view_conversation(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        outsider = User.objects.create_user(username="outsider1", password="StrongPass123")
        conversation = Conversation.objects.create(item=self.item, participant=participant)
        self.client.login(username="outsider1", password="StrongPass123")

        response = self.client.get(reverse("conversation_detail", args=[conversation.pk]))

        self.assertRedirects(response, reverse("conversation_list"))
        self.assertEqual(outsider.item_conversations.count(), 0)

    def test_conversation_list_shows_user_chats(self):
        participant = User.objects.create_user(
            username="participant1",
            password="StrongPass123",
        )
        Conversation.objects.create(item=self.item, participant=participant)
        self.client.login(username="participant1", password="StrongPass123")

        response = self.client.get(reverse("conversation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lost Laptop")
        self.assertContains(response, "staff1")

    def test_reporting_user_can_edit_item(self):
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.post(
            reverse("item_edit", args=[self.item.pk]),
            {
                "title": "Updated Laptop",
                "description": self.item.description,
                "category": self.item.category,
                "location": self.item.location,
                "event_date": "2026-04-28",
            },
        )

        self.assertRedirects(response, reverse("item_detail", args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Updated Laptop")

    def test_non_reporting_user_cannot_edit_item(self):
        User.objects.create_user(username="other1", password="StrongPass123")
        self.client.login(username="other1", password="StrongPass123")

        response = self.client.post(
            reverse("item_edit", args=[self.item.pk]),
            {
                "title": "Unauthorized Update",
                "description": self.item.description,
                "category": self.item.category,
                "location": self.item.location,
                "event_date": "2026-04-28",
            },
        )

        self.assertRedirects(response, reverse("item_list"))
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Lost Laptop")

    def test_reporting_user_can_delete_item(self):
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.post(reverse("item_delete", args=[self.item.pk]))

        self.assertRedirects(response, reverse("item_list"))
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_non_reporting_user_cannot_delete_item(self):
        User.objects.create_user(username="other1", password="StrongPass123")
        self.client.login(username="other1", password="StrongPass123")

        response = self.client.post(reverse("item_delete", args=[self.item.pk]))

        self.assertRedirects(response, reverse("item_list"))
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_claimant_can_submit_claim_for_found_item(self):
        claimant = User.objects.create_user(username="claimant1", password="StrongPass123")
        self.client.login(username="claimant1", password="StrongPass123")

        response = self.client.post(
            reverse("submit_claim", args=[self.found_item.pk]),
            {
                "verification_answer": "blue mountain",
                "proof_details": "The phone has a cracked top corner.",
            },
        )

        self.assertRedirects(response, reverse("item_detail", args=[self.found_item.pk]))
        claim = Claim.objects.get(item=self.found_item, claimant=claimant)
        self.assertTrue(claim.answer_matches)
        self.assertEqual(claim.status, Claim.Status.PENDING)

    def test_reporter_can_approve_claim(self):
        claimant = User.objects.create_user(username="claimant1", password="StrongPass123")
        claim = Claim.objects.create(
            item=self.found_item,
            claimant=claimant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.post(
            reverse("review_claim", args=[claim.pk, Claim.Status.APPROVED])
        )

        self.assertRedirects(response, reverse("item_detail", args=[self.found_item.pk]))
        claim.refresh_from_db()
        self.found_item.refresh_from_db()
        self.assertEqual(claim.status, Claim.Status.APPROVED)
        self.assertEqual(self.found_item.status, Item.Status.CLAIMED)

    def test_reporter_can_see_claimant_identity(self):
        claimant = User.objects.create_user(username="claimant1", password="StrongPass123")
        Profile.objects.create(
            user=claimant,
            role=Profile.Role.STUDENT,
            phone_number="0700000000",
            identification_number="STU-CLAIM",
        )
        Claim.objects.create(
            item=self.found_item,
            claimant=claimant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.client.login(username="staff1", password="StrongPass123")

        response = self.client.get(reverse("item_detail", args=[self.found_item.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "claimant1")
        self.assertContains(response, "STU-CLAIM")

    def test_admin_dashboard_loads_for_staff(self):
        self.client.login(username="admin1", password="StrongPass123")

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")
        self.assertContains(response, "Recent conversations")
        self.assertNotContains(response, "Returned items")

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
