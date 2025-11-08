"""Utility helpers that power smart counselor assignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
import re
from typing import List, Optional, Sequence

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from tccweb.core.models import Report, ReportStatus, ReportType

from .models import CounselorProfile, CounselorSpecialization

User = get_user_model()


@dataclass(frozen=True)
class CounselorCandidate:
    """Lightweight container for ranking counselor options."""

    profile: CounselorProfile
    active_cases: int
    specialization_rank: int
    last_auto_assigned_at: Optional[datetime]

    @property
    def user(self):
        return self.profile.user

    @property
    def user_id(self):
        return self.profile.user_id


SPECIALIZATION_RULES = {
    ReportType.BULLYING: CounselorSpecialization.DISCIPLINARY,
    ReportType.RAGGING: CounselorSpecialization.DISCIPLINARY,
    ReportType.HARASSMENT: CounselorSpecialization.EMOTIONAL,
}


def _target_specialization(report: Report) -> CounselorSpecialization:
    return SPECIALIZATION_RULES.get(report.incident_type, CounselorSpecialization.GENERAL)


def _collect_staff_profiles() -> List[CounselorProfile]:
    staff_ids = list(
        User.objects.filter(is_staff=True, is_active=True).values_list("id", flat=True)
    )
    if not staff_ids:
        return []

    profiles = {
        profile.user_id: profile
        for profile in CounselorProfile.objects.select_related("user").filter(
            user_id__in=staff_ids
        )
    }
    missing = [sid for sid in staff_ids if sid not in profiles]
    for user_id in missing:
        profile, _created = CounselorProfile.objects.get_or_create(user_id=user_id)
        profiles[user_id] = profile
    return list(profiles.values())


def _build_candidates(report: Report) -> List[CounselorCandidate]:
    profiles = [
        profile
        for profile in _collect_staff_profiles()
        if profile.auto_assign_enabled and profile.user.is_staff and profile.user.is_active
    ]
    if not profiles:
        return []

    workloads = {
        row["assigned_to"]: row["active"]
        for row in Report.objects.filter(
            assigned_to_id__in=[p.user_id for p in profiles]
        )
        .exclude(status=ReportStatus.RESOLVED)
        .values("assigned_to")
        .annotate(active=Count("id"))
    }

    target = _target_specialization(report)

    candidates: List[CounselorCandidate] = []
    for profile in profiles:
        active_cases = workloads.get(profile.user_id, 0)
        if active_cases >= profile.max_active_cases:
            continue
        if profile.specialization == target:
            specialization_rank = 0
        elif profile.specialization == CounselorSpecialization.GENERAL:
            specialization_rank = 1
        else:
            specialization_rank = 2
        candidates.append(
            CounselorCandidate(
                profile=profile,
                active_cases=active_cases,
                specialization_rank=specialization_rank,
                last_auto_assigned_at=profile.last_auto_assigned_at,
            )
        )
    return candidates


def _notify_assignment(report: Report, counselor) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{counselor.pk}",
        {
            "type": "notify",
            "data": {
                "title": "\ud83d\dd39 New case assigned",
                "body": f"Report #{report.id} needs your attention.",
                "url": reverse("counselor_case_detail", args=[report.id]),
            },
        },
    )


def assign_counselor(report: Report) -> None:
    """Assign the optimal counselor to a report if possible."""

    if report.assigned_to_id:
        return

    candidates = _build_candidates(report)
    if not candidates:
        return

    candidates.sort(
        key=lambda c: (
            c.specialization_rank,
            c.active_cases,
            c.last_auto_assigned_at or datetime.min.replace(tzinfo=dt_timezone.utc),
            c.user_id,
        )
    )

    chosen = candidates[0]

    with transaction.atomic():
        report.refresh_from_db(fields=["assigned_to_id"])
        if report.assigned_to_id:
            return
        report.assigned_to = chosen.user
        report.status = ReportStatus.UNDER_REVIEW
        report.save(update_fields=["assigned_to", "status"])
        chosen.profile.mark_assigned_now()

    _notify_assignment(report, chosen.user)


SUGGESTION_RULES = [
    {
        "keywords": (r"\bdepress(ed|ion)?\b", r"\bhopeless\b", r"\bworthless\b"),
        "tone": "Offer empathy",
        "responses": [
            "I'm really sorry you're feeling this way. Would you like to share more about what's been weighing on you lately?",
            "Thank you for opening up about these feelings. You're not alone and I'm here to help you find the next steps.",
        ],
    },
    {
        "keywords": (r"\banxious\b", r"\banxiety\b", r"\bpanic\b"),
        "tone": "Grounding support",
        "responses": [
            "It sounds like things feel overwhelming right now. Let's take it one step at a time—what tends to help you feel a little calmer?",
            "Thank you for sharing your worries. We can make a plan together to manage what's causing the anxiety.",
        ],
    },
    {
        "keywords": (r"\bstress(ed)?\b", r"\boverwhelm(ed|ing)?\b", r"\bpressure\b"),
        "tone": "Normalize and plan",
        "responses": [
            "That sounds like a lot to carry. Let's talk about what's adding the most pressure so we can explore some options together.",
            "Feeling stretched thin is completely understandable. Would it help if we prioritized a few next steps together?",
        ],
    },
    {
        "keywords": (r"\bharm myself\b", r"\bsuicid(al|e)\b", r"\bend my life\b", r"\bkill myself\b"),
        "tone": "Assess safety",
        "responses": [
            "I'm really concerned for your safety. Are you in immediate danger right now or have you already taken any steps to hurt yourself?",
            "Your safety is my top priority. Let's talk about what support you need in this moment—can I help connect you with urgent resources?",
        ],
    },
    {
        "keywords": (r"\bbully(ing)?\b", r"\bharass(ed|ment)?\b", r"\bthreat\b"),
        "tone": "Validate experience",
        "responses": [
            "I'm sorry you're experiencing this treatment. You deserve to feel safe—can you share more about what's been happening?",
            "Thank you for letting me know. Let's document the details together so we can respond quickly and keep you protected.",
        ],
    },
]

FALLBACK_RESPONSES: Sequence[str] = (
    "I appreciate you sharing this with me. What feels most important for us to focus on together right now?",
    "Thank you for reaching out—I'm here to support you. How have things been since this started?",
    "I'm listening. What would feel most helpful for you in the next day or two?",
)


def _match_rule(message: str, pattern: str) -> bool:
    try:
        return re.search(pattern, message) is not None
    except re.error:
        return False


def generate_suggested_replies(message: str, limit: int = 3) -> List[dict]:
    """Return human-editable reply suggestions based on message keywords."""

    normalized = (message or "").strip().lower()
    if not normalized:
        return []

    suggestions: List[dict] = []
    for rule in SUGGESTION_RULES:
        if any(_match_rule(normalized, pattern) for pattern in rule["keywords"]):
            for response in rule["responses"]:
                suggestions.append({"text": response, "tone": rule.get("tone", "Suggested")})
                if len(suggestions) >= limit:
                    return suggestions

    if len(suggestions) < limit:
        for response in FALLBACK_RESPONSES:
            suggestions.append({"text": response, "tone": "Supportive"})
            if len(suggestions) >= limit:
                break

    return suggestions