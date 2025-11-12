"""Core views shared across multiple portals."""

from __future__ import annotations

import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, resolve_url
from django.urls import NoReverseMatch
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from .utils import (
    build_two_factor_context,
    generate_totp_qr_data_uri,
    get_totp_model,
    get_user_totp_devices,
)


class EnableTwoFactorView(LoginRequiredMixin, TemplateView):
    """Guide users through enabling an authenticator-based 2FA flow."""

    template_name = "core/enable_two_factor.html"
    pending_session_key = "two_factor_pending_totp_device_id"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self._totp_model = get_totp_model()
        if self._totp_model is None:
            messages.error(
                request,
                "Two-factor authentication is not available. Please contact an"
                " administrator to finish configuring authenticator support.",
            )
            return redirect(self._default_return_url())

        return super().dispatch(request, *args, **kwargs)

    # ------------------------------------------------------------------ helpers
    def _default_return_url(self) -> str:
        try:
            return resolve_url("profile")
        except NoReverseMatch:
            return resolve_url("index")

    def _safe_url(self, candidate: str) -> str:
        if not candidate:
            return ""
        if url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return candidate
        return ""

    def _get_pending_device(self):
        pending_id = self.request.session.get(self.pending_session_key)
        if not pending_id:
            return None

        try:
            return self._totp_model.objects.get(  # type: ignore[attr-defined]
                pk=pending_id,
                user=self.request.user,
                confirmed=False,
            )
        except self._totp_model.DoesNotExist:  # type: ignore[attr-defined]
            self.request.session.pop(self.pending_session_key, None)
            self.request.session.modified = True
            return None

    def _device_display_name(self) -> str:
        issuer = getattr(settings, "OTP_TOTP_ISSUER", None) or getattr(
            settings, "SITE_NAME", "Safe Campus"
        )
        return f"{issuer} authenticator"

    def _clear_pending_device(self) -> None:
        pending_id = self.request.session.pop(self.pending_session_key, None)
        if pending_id:
            self._totp_model.objects.filter(  # type: ignore[attr-defined]
                pk=pending_id,
                user=self.request.user,
                confirmed=False,
            ).delete()
        else:
            self._totp_model.objects.filter(  # type: ignore[attr-defined]
                user=self.request.user,
                confirmed=False,
            ).delete()
        self.request.session.modified = True

    def _ensure_pending_device(self):
        device = self._get_pending_device()
        if device is not None:
            return device

        self._totp_model.objects.filter(  # type: ignore[attr-defined]
            user=self.request.user,
            confirmed=False,
        ).delete()
        device = self._totp_model.objects.create(  # type: ignore[attr-defined]
            user=self.request.user,
            name=self._device_display_name(),
            confirmed=False,
        )
        self.request.session[self.pending_session_key] = device.pk
        self.request.session.modified = True
        return device

    def _format_manual_key(self, key: str) -> str:
        key = (key or "").replace(" ", "").upper()
        return " ".join(key[i : i + 4] for i in range(0, len(key), 4)).strip()

    def _update_profile_flag(self, enabled: bool) -> None:
        profile = getattr(self.request.user, "profile", None)
        if profile and getattr(profile, "two_factor_enabled", None) is not None:
            if profile.two_factor_enabled != enabled:
                profile.two_factor_enabled = enabled
                profile.save(update_fields=["two_factor_enabled"])

    # ----------------------------------------------------------------- overrides
    def get_success_url(self) -> str:
        next_value = self._safe_url(
            self.request.POST.get("next") or self.request.GET.get("next", "")
        )
        if next_value:
            return next_value
        referer = self._safe_url(self.request.META.get("HTTP_REFERER", ""))
        if referer:
            return referer
        return self._default_return_url()

    def get_context_data(self, **kwargs):  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        safe_referer = self._safe_url(self.request.META.get("HTTP_REFERER", ""))
        safe_next = self._safe_url(
            self.request.GET.get("next", "") or self.request.POST.get("next", "")
        )
        fallback_url = self._default_return_url()

        context.update(build_two_factor_context(self.request.user))
        context["two_factor_devices"] = get_user_totp_devices(
            self.request.user, confirmed=True
        )
        context["two_factor_device_count"] = len(context["two_factor_devices"])
        context.update(
            {
                "two_factor_return_url": safe_referer or fallback_url,
                "two_factor_next_value": safe_next,
                "two_factor_fallback_url": fallback_url,
            }
        )

        if not context.get("two_factor_enabled"):
            pending_device = self._ensure_pending_device()
            manual_key = getattr(pending_device, "key", "")
            if isinstance(manual_key, bytes):
                manual_key = manual_key.decode()
            manual_key = manual_key.replace(" ", "").upper()

            config_value = getattr(pending_device, "config_url", "")
            if callable(config_value):
                try:
                    config_value = config_value()
                except TypeError:  # pragma: no cover - defensive guard
                    config_value = ""

            context.update(
                {
                    "two_factor_pending_device": pending_device,
                    "two_factor_otpauth_url": config_value,
                    "two_factor_manual_key": manual_key,
                    "two_factor_manual_key_spaced": self._format_manual_key(manual_key),
                    "two_factor_device_label": pending_device.name
                    or self._device_display_name(),
                    "two_factor_qr_code_data_uri": generate_totp_qr_data_uri(
                        config_value
                    ),
                }
            )

        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        action = request.POST.get("action", "verify")

        if action == "disable":
            for device in get_user_totp_devices(request.user):
                device.delete()
            self._clear_pending_device()
            self._update_profile_flag(False)
            messages.info(
                request,
                "Two-factor authentication has been disabled. Re-enable it as"
                " soon as possible to keep student data protected.",
            )
            return redirect(self.get_success_url())

        if action == "refresh":
            self._clear_pending_device()
            self._ensure_pending_device()
            messages.success(
                request,
                "Generated a new authenticator key. Scan the new QR code or"
                " enter the updated setup key below.",
            )
            return redirect(request.path)

        # Default behaviour is to verify the submitted token and enable 2FA.
        raw_token = request.POST.get("otp_token") or ""
        # Normalise the one-time password by stripping whitespace so users can
        # paste values with spaces or line breaks from their authenticator app.
        token = re.sub(r"\s+", "", raw_token)

        if not token:
            messages.error(
                request,
                "Enter the six-digit code from your authenticator app to"
                " finish enabling two-factor authentication.",
            )
            return self.render_to_response(self.get_context_data(**kwargs))

        if not token.isdigit():
            messages.error(
                request,
                "Authenticator codes should only contain numbers. Check the"
                " code displayed in your app and try again.",
            )
            return self.render_to_response(self.get_context_data(**kwargs))

        pending_device = self._get_pending_device()
        if pending_device is None:
            pending_device = self._ensure_pending_device()

        verified = False
        if pending_device is not None:
            # Allow projects to tweak the tolerated clock drift via Django
            # settings while staying compatible with older django-otp releases
            # whose ``verify_token`` implementation does not accept the
            # ``tolerance`` keyword argument.
            verify_kwargs = {}
            tolerance = getattr(settings, "OTP_TOTP_TOLERANCE", None)
            if tolerance is not None:
                verify_kwargs["tolerance"] = tolerance

            try:
                if hasattr(pending_device, "verify_is_allowed") and not pending_device.verify_is_allowed():
                    messages.error(
                        request,
                        "Too many incorrect codes. Please wait a moment before"
                        " trying again.",
                    )
                    return self.render_to_response(self.get_context_data(**kwargs))

                verified = pending_device.verify_token(token, **verify_kwargs)
            except TypeError:
                # Older django-otp signatures do not accept ``tolerance``.
                verified = pending_device.verify_token(token)
            except Exception:
                verified = False

        if verified:
            pending_device.confirmed = True
            pending_device.save(update_fields=["confirmed"])
            self._clear_pending_device()
            self._totp_model.objects.filter(  # type: ignore[attr-defined]
                user=request.user,
                confirmed=False,
            ).exclude(pk=pending_device.pk).delete()
            self._update_profile_flag(True)
            messages.success(
                request,
                "Two-factor authentication is now enabled. You will be asked"
                " for a verification code the next time you sign in.",
            )
            return redirect(self.get_success_url())

        messages.error(
            request,
            "That code was invalid or expired. Generate a fresh code in your"
            " authenticator app and try again.",
        )
        return self.render_to_response(self.get_context_data(**kwargs))


__all__ = ["EnableTwoFactorView"]