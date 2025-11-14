from __future__ import annotations

from copy import deepcopy

from django import template
from django.forms import BoundField

register = template.Library()


def _normalize_classes(existing: str, extra: str) -> str:
    classes = list(dict.fromkeys(f"{existing} {extra}".split()))
    return " ".join(classes)


_DEFERRED_HELP_TEXT_FIELDS = {"username", "password1", "password2"}


_DEFERRED_HELP_TEXT_DEPENDENCIES = {
    "username": ("username",),
    "password1": ("password1", "password2"),
    "password2": ("password2",),
}


def _clone_with_classes(field: BoundField, css_classes: str):
    attrs = deepcopy(getattr(field.field.widget, "attrs", {}))
    existing = attrs.get("class", "")
    attrs["class"] = _normalize_classes(existing, css_classes)
    return field.as_widget(attrs=attrs)


@register.filter(name="add_css")
def add_css(field, css_classes: str):
    """Render the field widget with the provided CSS classes appended."""

    if not isinstance(field, BoundField):
        return field

    return _clone_with_classes(field, css_classes)


@register.filter(name="add_class")
def add_class(field, css_classes: str):
    """Compatibility alias matching widget_tweaks' add_class filter name."""

    if not isinstance(field, BoundField):
        return field

    return _clone_with_classes(field, css_classes)


@register.filter(name="defer_help_text")
def defer_help_text(field):
    """Return True when help text should only display after validation errors."""

    return isinstance(field, BoundField) and field.name in _DEFERRED_HELP_TEXT_FIELDS


@register.filter(name="should_show_deferred_help")
def should_show_deferred_help(field):
    """Return True when deferred help text should be displayed for the field."""

    if not isinstance(field, BoundField):
        return False

    if field.name not in _DEFERRED_HELP_TEXT_FIELDS:
        return False

    form = field.form
    if not getattr(form, "is_bound", False):
        return False

    dependent_fields = _DEFERRED_HELP_TEXT_DEPENDENCIES.get(field.name, (field.name,))

    for dependency in dependent_fields:
        if form.errors.get(dependency):
            return True

    return False