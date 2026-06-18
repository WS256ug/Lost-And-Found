import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Profile
from items.models import Claim, Conversation, Item, Message, Notification


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MobileAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.reporter = User.objects.create_user(
            username="reporter1",
            email="reporter@example.com",
            password="StrongPass123",
        )
        self.participant = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="StrongPass123",
        )
        self.outsider = User.objects.create_user(
            username="outsider1",
            password="StrongPass123",
        )
        Profile.objects.create(
            user=self.reporter,
            role=Profile.Role.STUDENT,
            identification_number="STU-001",
        )
        Profile.objects.create(
            user=self.participant,
            role=Profile.Role.STUDENT,
            identification_number="STU-002",
        )
        Profile.objects.create(
            user=self.outsider,
            role=Profile.Role.STUDENT,
            identification_number="STU-003",
        )
        self.item = Item.objects.create(
            report_type=Item.ReportType.LOST,
            title="Lost Laptop",
            description="Black Dell laptop",
            category=Item.Category.ELECTRONICS,
            location="Library",
            event_date="2026-04-28",
            status=Item.Status.LOST,
            reported_by=self.reporter,
        )

    def create_found_item(self):
        item = Item.objects.create(
            report_type=Item.ReportType.FOUND,
            title="Found Phone",
            description="Phone found near the cafeteria",
            category=Item.Category.ELECTRONICS,
            location="Cafeteria",
            event_date="2026-04-29",
            status=Item.Status.FOUND,
            reported_by=self.reporter,
            verification_question="What is on the lock screen?",
        )
        item.set_verification_answer("blue mountain")
        item.save()
        return item

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_register_creates_user_profile_and_tokens(self):
        response = self.client.post(
            reverse("api-register"),
            {
                "username": "newstudent",
                "email": "newstudent@example.com",
                "password": "StrongPass123",
                "phone_number": "0712345678",
                "identification_number": "STU-2026-010",
                "role": Profile.Role.STUDENT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data["tokens"])
        user = User.objects.get(username="newstudent")
        self.assertEqual(user.profile.identification_number, "STU-2026-010")

    def test_login_returns_jwt_tokens(self):
        response = self.client.post(
            reverse("api-login"),
            {
                "username": "student1",
                "password": "StrongPass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_public_item_list_supports_search_and_filters(self):
        self.create_found_item()

        response = self.client.get(
            reverse("api-item-list"),
            {"q": "phone", "status": Item.Status.FOUND, "type": Item.ReportType.FOUND},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["public_label"], "Found item")
        self.assertNotIn("title", response.data[0])
        self.assertNotIn("description", response.data[0])
        self.assertNotIn("location", response.data[0])
        self.assertNotIn("category", response.data[0])

    def test_public_found_item_detail_hides_private_fields(self):
        item = self.create_found_item()

        response = self.client.get(reverse("api-item-detail", args=[item.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["public_label"], "Found item")
        self.assertNotIn("title", response.data)
        self.assertNotIn("description", response.data)
        self.assertNotIn("location", response.data)
        self.assertNotIn("reported_by", response.data)

    def test_public_item_list_does_not_expose_lost_reports(self):
        response = self.client.get(
            reverse("api-item-list"),
            {"type": Item.ReportType.LOST},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_uninvolved_user_cannot_view_lost_item_detail(self):
        self.authenticate(self.participant)

        response = self.client.get(reverse("api-item-detail", args=[self.item.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_can_create_item_with_image(self):
        self.authenticate(self.participant)
        image_bytes = (
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00"
            b"\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00"
            b"\x00\x02\x02D\x01\x00;"
        )
        image = SimpleUploadedFile(
            "phone.gif",
            image_bytes,
            content_type="image/gif",
        )

        response = self.client.post(
            reverse("api-item-list"),
            {
                "report_type": Item.ReportType.FOUND,
                "title": "Found Phone",
                "description": "Found near the cafeteria.",
                "category": Item.Category.ELECTRONICS,
                "location": "Cafeteria",
                "event_date": "2026-04-29",
                "image": image,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = Item.objects.get(title="Found Phone")
        self.assertEqual(item.reported_by, self.participant)
        self.assertEqual(item.status, Item.Status.FOUND)
        self.assertTrue(item.image.name.startswith("item_images/"))
        self.assertEqual(item.image_data, image_bytes)
        self.assertEqual(item.image_content_type, "image/gif")
        self.assertIn(
            reverse("item_image", args=[item.pk]),
            response.data["image_url"],
        )

    def test_unauthenticated_user_cannot_create_item(self):
        response = self.client.post(
            reverse("api-item-list"),
            {
                "report_type": Item.ReportType.LOST,
                "title": "Lost ID",
                "description": "Student ID card.",
                "category": Item.Category.ID_CARDS,
                "location": "Main gate",
                "event_date": "2026-04-30",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_start_conversation_for_protected_found_item(self):
        item = self.create_found_item()
        self.authenticate(self.participant)

        response = self.client.post(
            reverse("api-item-start-conversation", args=[item.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Conversation.objects.exists())

    def test_user_can_submit_claim_for_found_item(self):
        item = self.create_found_item()
        self.authenticate(self.participant)

        response = self.client.post(
            reverse("api-item-claims", args=[item.pk]),
            {
                "verification_answer": "blue mountain",
                "proof_details": "The phone has a cracked top corner.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claim = Claim.objects.get(item=item, claimant=self.participant)
        self.assertTrue(claim.answer_matches)
        self.assertEqual(response.data["status"], Claim.Status.PENDING)

    def test_claim_submission_notifies_reporter(self):
        item = self.create_found_item()
        self.authenticate(self.participant)

        response = self.client.post(
            reverse("api-item-claims", args=[item.pk]),
            {
                "verification_answer": "blue mountain",
                "proof_details": "The phone has a cracked top corner.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(
            recipient=self.reporter,
            notification_type=Notification.Type.CLAIM_SUBMITTED,
        )
        self.assertEqual(notification.actor, self.participant)
        self.assertEqual(notification.item, item)

        self.authenticate(self.reporter)
        list_response = self.client.get(reverse("api-notification-list"))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["title"], "New claim submitted")
        self.assertFalse(list_response.data[0]["is_read"])

    def test_reporter_can_approve_claim(self):
        item = self.create_found_item()
        claim = Claim.objects.create(
            item=item,
            claimant=self.participant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.authenticate(self.reporter)

        response = self.client.post(
            reverse("api-claim-review", args=[claim.pk]),
            {"status": Claim.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(claim.status, Claim.Status.APPROVED)
        self.assertEqual(item.status, Item.Status.CLAIMED)

    def test_claim_review_notifies_claimant(self):
        item = self.create_found_item()
        claim = Claim.objects.create(
            item=item,
            claimant=self.participant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.authenticate(self.reporter)

        response = self.client.post(
            reverse("api-claim-review", args=[claim.pk]),
            {"status": Claim.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(
            recipient=self.participant,
            notification_type=Notification.Type.CLAIM_APPROVED,
        )
        self.assertEqual(notification.actor, self.reporter)
        self.assertEqual(notification.claim, claim)

    def test_user_can_mark_notification_read(self):
        item = self.create_found_item()
        claim = Claim.objects.create(
            item=item,
            claimant=self.participant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        notification = Notification.objects.create(
            recipient=self.reporter,
            actor=self.participant,
            notification_type=Notification.Type.CLAIM_SUBMITTED,
            title="New claim submitted",
            message="student1 submitted a claim for your found item.",
            item=item,
            claim=claim,
        )
        self.authenticate(self.reporter)

        response = self.client.post(
            reverse("api-notification-read", args=[notification.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_reporter_can_see_who_claimed_item(self):
        item = self.create_found_item()
        claim = Claim.objects.create(
            item=item,
            claimant=self.participant,
            proof_details="The phone has a cracked top corner.",
            answer_matches=True,
        )
        self.authenticate(self.reporter)

        response = self.client.get(reverse("api-claim-detail", args=[claim.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["claimant"]["username"], "student1")
        self.assertEqual(
            response.data["claimant_profile"]["identification_number"],
            "STU-002",
        )

    def test_reporter_cannot_start_conversation_with_own_item(self):
        self.authenticate(self.reporter)

        response = self.client.post(
            reverse("api-item-start-conversation", args=[self.item.pk]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Conversation.objects.exists())

    def test_conversation_member_can_send_message(self):
        conversation = Conversation.objects.create(
            item=self.item,
            participant=self.participant,
        )
        self.authenticate(self.participant)

        response = self.client.post(
            reverse("api-conversation-messages", args=[conversation.pk]),
            {"body": "Hi, I think this laptop may be mine."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.sender, self.participant)
        self.assertEqual(message.body, "Hi, I think this laptop may be mine.")

    def test_outsider_cannot_view_conversation(self):
        conversation = Conversation.objects.create(
            item=self.item,
            participant=self.participant,
        )
        self.authenticate(self.outsider)

        response = self.client.get(
            reverse("api-conversation-detail", args=[conversation.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
