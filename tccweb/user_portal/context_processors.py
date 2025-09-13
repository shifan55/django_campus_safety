from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.db.utils import OperationalError

ChatMessage = AdminAlert = None
if apps.is_installed("tccweb.counselor_portal"):
    try:  # counselor_portal may be absent during some admin-only operations
        ChatMessage = apps.get_model("counselor_portal", "ChatMessage")
        AdminAlert = apps.get_model("counselor_portal", "AdminAlert")
    except Exception:  # pragma: no cover - handled gracefully
        ChatMessage = AdminAlert = None


def google_maps_key(request):
    return {"GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", "")}


def unread_messages(request):
    """Provide unread message count and admin alerts via the messages framework."""
    if not request.user.is_authenticated or ChatMessage is None:
        return {"unread_messages": 0, "admin_alerts": 0}

    try:
        count = ChatMessage.objects.filter(recipient=request.user, is_read=False).count()
    except OperationalError:
        # Database not migrated for messaging tables
        return {"unread_messages": 0, "admin_alerts": 0}
    admin_alerts = 0

    if request.user.is_superuser and AdminAlert is not None:
        try:
            alerts = AdminAlert.objects.filter(admin=request.user, is_read=False)
            admin_alerts = alerts.count()
        except OperationalError:
            alerts = []
            admin_alerts = 0
        for alert in alerts:
            snippet = (alert.message[:97] + "...") if len(alert.message) > 100 else alert.message
            messages.warning(
                request,
                f"Report #{alert.report_id} resolved: {snippet}",
            )
        if admin_alerts:
            alerts.update(is_read=True)

    if count:
        messages.info(
            request,
            f"You have {count} unread message{'s' if count != 1 else ''}.",
        )
    return {"unread_messages": count, "admin_alerts": admin_alerts}