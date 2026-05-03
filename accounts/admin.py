from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    can_delete = False
    verbose_name_plural = "Profile details"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "phone_number",
        "identification_number",
    )
    list_filter = ("role",)
    search_fields = (
        "user__username",
        "user__email",
        "phone_number",
        "identification_number",
    )
    list_select_related = ("user",)
    ordering = ("user__username",)
    autocomplete_fields = ("user",)

    @admin.display(ordering="user__username", description="Username")
    def username(self, obj):
        return obj.user.username

    @admin.display(ordering="user__email", description="Email")
    def email(self, obj):
        return obj.user.email


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
