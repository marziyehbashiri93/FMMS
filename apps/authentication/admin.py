"""Authentication admin registration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.authentication.infrastructure.models import FMMSUser


@admin.register(FMMSUser)
class FMMSUserAdmin(UserAdmin):
    """Admin interface for FMMSUser."""

    model = FMMSUser
    list_display = [
        "username",
        "email",
        "full_name",
        "role",
        "personnel_number",
        "is_active",
        "is_staff",
        "created_at",
    ]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "email", "full_name", "personnel_number"]
    ordering = ["full_name"]

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Personal", {"fields": ("full_name",)}),
        ("FMMS", {"fields": ("role", "personnel_number")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["created_at", "updated_at"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "full_name",
                    "role",
                    "personnel_number",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
