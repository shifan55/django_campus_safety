from django import template
from tccweb.counselor_portal.models import ChatMessage

register = template.Library()


@register.filter
def decrypt(message: ChatMessage, user):
    """Decrypt a ChatMessage for the given user."""
    if not isinstance(message, ChatMessage):
        return ""
    try:
        return message.get_body_for(user)
    except Exception:
        return ""