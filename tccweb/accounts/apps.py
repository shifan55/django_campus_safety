from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tccweb.accounts"

    def ready(self) -> None:
        # Import signal handlers
        from . import models  # noqa: F401