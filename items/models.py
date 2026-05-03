from django.conf import settings
from django.db import models


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
