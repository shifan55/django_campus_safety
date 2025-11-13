"""Custom adapters for third-party integrations."""
from __future__ import annotations

import logging
from typing import Any

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured, MultipleObjectsReturned

logger = logging.getLogger(__name__)


class CampusSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Harden SocialApp selection when duplicates exist."""

    def get_app(self, request, provider: str, client_id: str | None = None) -> SocialApp:
        try:
            return super().get_app(request, provider, client_id=client_id)
        except MultipleObjectsReturned:
            return self._resolve_first_social_app(request, provider, client_id)

    def _resolve_first_social_app(
        self, request: Any, provider: str, client_id: str | None
    ) -> SocialApp:
        apps = SocialApp.objects.filter(provider=provider)

        if client_id:
            apps = apps.filter(client_id=client_id)

        site = self._safe_get_current_site(request)
        scoped_apps = apps
        if site is not None:
            scoped_apps = apps.filter(sites=site)

        social_app = scoped_apps.order_by("id").first()
        if social_app is None:
            # Fall back to a global lookup in case the duplicate entries are
            # spread across different sites.
            social_app = apps.order_by("id").first()

        if social_app is None:
            # If we got here, something changed between the query that raised the
            # exception and our follow-up query. Surface the original error.
            raise MultipleObjectsReturned(
                "Unable to select a SocialApp after resolving duplicates."
            )

        logger.warning(
            "Multiple SocialApp entries detected for provider '%s' (site=%s, client_id=%s); using SocialApp id=%s",
            provider,
            getattr(site, "id", None),
            client_id,
            social_app.id,
        )
        return social_app

    def _safe_get_current_site(self, request: Any) -> Site | None:
        try:
            site = get_current_site(request)
        except (ImproperlyConfigured, Site.DoesNotExist):
            logger.warning(
                "Could not determine current Site while resolving SocialApp duplicates; continuing without site filtering.",
            )
            return None
        return site