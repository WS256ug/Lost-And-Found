from django.contrib import admin
from django.utils.html import format_html

from .models import Claim, Conversation, Item, Message, Notification


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "title",
        "report_type",
        "category",
        "status",
        "has_verification_question",
        "location",
        "event_date",
        "reported_by",
        "created_at",
    )
    list_filter = ("report_type", "category", "status", "event_date")
    search_fields = ("title", "description", "location", "reported_by__username")
    list_select_related = ("reported_by",)
    ordering = ("-created_at",)
    date_hierarchy = "event_date"
    list_per_page = 25
    readonly_fields = ("image_preview_large", "created_at", "updated_at")

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" alt="{}" style="width: 56px; height: 56px; object-fit: cover; border-radius: 8px;" />',
                obj.image.url,
                obj.title,
            )
        return "No image"

    @admin.display(description="Image preview")
    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" alt="{}" style="max-width: 220px; max-height: 220px; object-fit: cover; border-radius: 12px;" />',
                obj.image.url,
                obj.title,
            )
        return "No image uploaded"

    @admin.display(boolean=True, description="Verification")
    def has_verification_question(self, obj):
        return obj.has_verification_question


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "claimant",
        "status",
        "answer_matches",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("status", "answer_matches", "created_at", "reviewed_at")
    search_fields = (
        "item__title",
        "claimant__username",
        "claimant__email",
        "proof_details",
    )
    list_select_related = ("item", "claimant", "reviewed_by")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
    ordering = ("-created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("item", "participant", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = (
        "item__title",
        "participant__username",
        "participant__email",
        "item__reported_by__username",
    )
    list_select_related = ("item", "participant", "item__reported_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body", "sender__username", "conversation__item__title")
    list_select_related = ("conversation", "conversation__item", "sender")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "notification_type",
        "recipient",
        "actor",
        "item",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = (
        "title",
        "message",
        "recipient__username",
        "actor__username",
        "item__title",
    )
    list_select_related = ("recipient", "actor", "item", "claim")
    readonly_fields = ("created_at", "read_at")
    ordering = ("-created_at",)
