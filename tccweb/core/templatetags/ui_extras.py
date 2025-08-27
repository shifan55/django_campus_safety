from django import template

register = template.Library()

def _to_value(obj):
    """
    Accept enums or plain strings.
    If it's an Enum or has `.value`, use that; else use the string itself.
    """
    try:
        return obj.value
    except Exception:
        return str(obj)

@register.filter
def humanize_enum(val):
    """
    Convert 'UNDER_REVIEW' or 'under_review' -> 'Under Review'
    """
    s = _to_value(val)
    return s.replace("_", " ").replace("-", " ").strip().title()

@register.filter
def status_badge(status):
    """
    Map status -> Bootstrap color name.
    pending -> warning
    under_review -> info
    resolved -> success
    (fallback) -> secondary
    """
    s = _to_value(status).lower()
    if s == "pending":
        return "warning"
    if s == "under_review":
        return "info"
    if s == "resolved":
        return "success"
    return "secondary"

@register.filter
def priority_badge(priority):
    """
    Map priority -> Bootstrap color name.
    urgent -> danger
    high -> warning
    medium -> info
    (fallback) -> secondary
    """
    p = _to_value(priority).lower()
    if p == "urgent":
        return "danger"
    if p == "high":
        return "warning"
    if p == "medium":
        return "info"
    return "secondary"
