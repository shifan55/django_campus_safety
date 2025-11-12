from django.contrib import admin

from .models import (
    EducationalResource,
    Report,
    SecurityLog,
    SupportContact,
    SystemLog,
)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    """Expose the immutable audit trail to administrators."""

    list_display = ("timestamp", "user", "action_type", "object_type", "object_id")
    list_filter = ("action_type", "object_type", "timestamp")
    search_fields = ("user__username", "user__email", "object_type", "object_id")
    readonly_fields = (
        "user",
        "timestamp",
        "action_type",
        "object_type",
        "object_id",
        "content_type",
        "description",
        "metadata",
    )
    ordering = ("-timestamp",)


admin.site.register(Report)
admin.site.register(EducationalResource)
admin.site.register(SupportContact)


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    """Expose authentication and permission events to administrators."""

    list_display = (
        "timestamp",
        "event_type",
        "actor",
        "target_user",
        "ip_address",
    )
    list_filter = ("event_type", "timestamp")
    search_fields = (
        "actor__username",
        "actor__email",
        "target_user__username",
        "target_user__email",
        "description",
    )
    readonly_fields = (
        "timestamp",
        "event_type",
        "actor",
        "target_user",
        "ip_address",
        "user_agent",
        "description",
        "metadata",
    )
    ordering = ("-timestamp",)