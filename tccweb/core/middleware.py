from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone


@dataclass
class AutoLogoutMiddleware:
    """Automatically log out inactive users and redirect to the homepage."""

    get_response: Callable[[HttpRequest], HttpResponse]

    def __post_init__(self) -> None:
        self.timeout_seconds = int(getattr(settings, "AUTO_LOGOUT_TIMEOUT", 60 * 5))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            now_ts = timezone.now().timestamp()
            last_activity = request.session.get("last_activity_ts")

            if isinstance(last_activity, (int, float)) and now_ts - last_activity > self.timeout_seconds:
                logout(request)
                messages.info(request, "You have been logged out due to inactivity.")
                return redirect("index")

            request.session["last_activity_ts"] = now_ts

        else:
            request.session.pop("last_activity_ts", None)

        response = self.get_response(request)
        return response