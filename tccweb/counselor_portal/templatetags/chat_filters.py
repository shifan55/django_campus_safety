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
    

@register.filter
def is_sender(message: ChatMessage, user) -> bool:
    """Return True when the given user authored the message."""
    if not isinstance(message, ChatMessage) or user is None:
        return False

    user_id = getattr(user, "id", None)
    sender_id = getattr(message, "sender_id", None)
    if user_id is None or sender_id is None:
        return False

    return sender_id == user_id