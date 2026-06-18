from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Item(models.Model):
    class ReportType(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"

    class Status(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"
        CLAIMED = "claimed", "Claimed"
        RETURNED = "returned", "Returned"

    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Electronics"
        DOCUMENTS = "documents", "Documents"
        ID_CARDS = "id_cards", "ID Cards"
        KEYS = "keys", "Keys"
        BOOKS = "books", "Books"
        CLOTHING = "clothing", "Clothing"
        OTHER = "other", "Other"

    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Category.choices)
    location = models.CharField(max_length=150)
    event_date = models.DateField()
    image = models.ImageField(upload_to="item_images/", blank=True, null=True)
    image_data = models.BinaryField(blank=True, null=True)
    image_content_type = models.CharField(max_length=100, blank=True)
    image_filename = models.CharField(max_length=255, blank=True)
    verification_question = models.CharField(max_length=255, blank=True)
    verification_answer_hash = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reported_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def has_verification_question(self):
        return bool(self.verification_question.strip())

    def set_verification_answer(self, raw_answer):
        answer = (raw_answer or "").strip()
        self.verification_answer_hash = make_password(answer) if answer else ""

    def store_image_file(self, image_file):
        if not image_file:
            return

        if hasattr(image_file, "seek"):
            image_file.seek(0)

        if hasattr(image_file, "chunks"):
            image_bytes = b"".join(image_file.chunks())
        else:
            image_bytes = image_file.read()

        if hasattr(image_file, "seek"):
            image_file.seek(0)

        self.image_data = image_bytes
        self.image_content_type = getattr(
            image_file,
            "content_type",
            "",
        ) or "application/octet-stream"
        self.image_filename = (getattr(image_file, "name", "") or "")[:255]

    def check_verification_answer(self, raw_answer):
        answer = (raw_answer or "").strip()
        if not self.verification_answer_hash or not answer:
            return False
        return check_password(answer, self.verification_answer_hash)

    def can_user_view_private_details(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or self.reported_by_id == user.id:
            return True
        return self.conversations.filter(participant=user).exists()


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    proof_details = models.TextField()
    answer_matches = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_claims",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "claimant"],
                name="unique_item_claimant_claim",
            )
        ]

    def __str__(self):
        return f"{self.claimant} claim for {self.item}"

    def review(self, reviewer, next_status, note=""):
        self.status = next_status
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note


class Conversation(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="item_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "participant"],
                name="unique_item_participant_conversation",
            )
        ]

    def __str__(self):
        return f"{self.item} conversation with {self.participant}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_item_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender} on {self.conversation.item}"


class Notification(models.Model):
    class Type(models.TextChoices):
        CLAIM_SUBMITTED = "claim_submitted", "Claim submitted"
        CLAIM_APPROVED = "claim_approved", "Claim approved"
        CLAIM_REJECTED = "claim_rejected", "Claim rejected"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(max_length=40, choices=Type.choices)
    title = models.CharField(max_length=150)
    message = models.TextField()
    item = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    claim = models.ForeignKey(
        Claim,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} for {self.recipient}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
