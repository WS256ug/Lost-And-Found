from django.contrib import admin
from django.utils.html import format_html

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "title",
        "report_type",
        "category",
        "status",
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
