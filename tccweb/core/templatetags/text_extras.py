from django import template

register = template.Library()

@register.filter
def humanize_enum(val):
    """Convert 'UNDER_REVIEW' -> 'Under Review'."""
    try:
        s = val.value
    except Exception:
        s = str(val)
    return s.replace("_", " ").replace("-", " ").strip().title()

@register.filter
def status_badge(status):
    s = getattr(status, "value", str(status)).lower()
    if s == "pending": return "warning"
    if s == "under_review": return "info"
    if s == "resolved": return "success"
    return "secondary"

@register.filter
def priority_badge(priority):
    p = getattr(priority, "value", str(priority)).lower()
    if p == "urgent": return "danger"
    if p == "high": return "warning"
    if p == "medium": return "info"
    return "secondary"
