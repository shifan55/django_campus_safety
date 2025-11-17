from collections import Counter
from datetime import datetime, timedelta
import csv
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import (
    login_required as auth_login_required,
    user_passes_test as auth_user_passes_test,
)
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import (
    Avg,
    Case as CaseExpression,
    CharField,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncMonth, TruncWeek
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.templatetags.static import static


from tccweb.core.models import (
    Report,
    ReportStatus,
    SystemLog,
)  # provides status choices for filtering
from .forms import CaseNoteForm
from tccweb.core.forms import MessageForm
from tccweb.core.utils import build_two_factor_context
from tccweb.core.mixins import AuditLogMixin
from .models import CaseNote, ChatMessage, AdminAlert, RiskLevel, EmotionLabel, CounselorProfile
from .services import generate_suggested_replies
from tccweb.accounts.forms import ProfileForm
from tccweb.accounts.models import Profile


logger = logging.getLogger(__name__)


def _safe_reverse(name: str, *args, **kwargs) -> str:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"

def _is_counselor(user):
    return user.is_staff or getattr(getattr(user, "profile", None), "is_staff", False)


@auth_login_required
@auth_user_passes_test(_is_counselor)
def dashboard(request):
    # Get both assigned reports and unassigned reports for the "New" queue
    reports_qs = (
        Report.objects.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
        )
        .select_related("reporter", "assigned_to")
    )
    
    status = request.GET.get("status")
    start = request.GET.get("start")
    end = request.GET.get("end")
    if status:
        reports_qs = reports_qs.filter(status=status)
    if start:
        reports_qs = reports_qs.filter(created_at__date__gte=start)
    if end:
        reports_qs = reports_qs.filter(created_at__date__lte=end)
        
    latest_message = (
        ChatMessage.objects.filter(report=OuterRef("pk"))
        .order_by("-timestamp")
    )
    reports_qs = reports_qs.annotate(
        latest_message_ts=Subquery(latest_message.values("timestamp")[:1]),
        latest_message_sender=Subquery(latest_message.values("sender")[:1]),
        has_unread=Exists(
            ChatMessage.objects.filter(
                report=OuterRef("pk"), recipient=request.user, is_read=False
            )
        ),
    )
    
    reports_qs = reports_qs.annotate(
        last_activity=Coalesce("latest_message_ts", "updated_at", "created_at")
    )

    queue_case = CaseExpression(
        When(status=ReportStatus.RESOLVED, then=Value("closed")),
        When(assigned_to__isnull=True, then=Value("new")),
        When(latest_message_sender=request.user.id, then=Value("waiting_on_student")),
        When(assigned_to=request.user, then=Value("assigned_to_me")),
        default=Value("assigned_to_me"),
        output_field=CharField(),
    )
    reports_qs = reports_qs.annotate(queue_state=queue_case)

    queue_priority = CaseExpression(
        When(queue_state="new", then=Value(0)),
        When(queue_state="assigned_to_me", then=Value(1)),
        When(queue_state="waiting_on_student", then=Value(2)),
        When(queue_state="closed", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    reports_qs = reports_qs.annotate(queue_priority=queue_priority)

    queue_counts_qs = reports_qs.values("queue_state").annotate(total=Count("id"))
    queue_counts = {row["queue_state"]: row["total"] for row in queue_counts_qs}

    metrics_qs = reports_qs
    queue_filter = request.GET.get("queue", "all")
    queue_metadata = {
        "new": {
            "label": "New",
            "description": "Unassigned reports/cases that no counselor has taken",
            "badge": "primary",
        },
        "assigned_to_me": {
            "label": "Assigned to Me",
            "description": "Reports currently being handled by you",
            "badge": "info",
        },
        "waiting_on_student": {
            "label": "Waiting on Student",
            "description": "Reports where you replied last and are waiting for student response",
            "badge": "warning",
        },
        "closed": {
            "label": "Closed",
            "description": "Completed, archived, or resolved reports",
            "badge": "success",
        },
    }

    if queue_filter and queue_filter != "all":
        reports_qs = reports_qs.filter(queue_state=queue_filter)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=assigned_reports.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Type", "Status", "Queue", "Assigned To", "Last Update", "Submitted"])
        for r in reports_qs:
            writer.writerow([
                r.id,
                r.get_incident_type_display(),
                r.get_status_display(),
                queue_metadata.get(r.queue_state, {}).get("label", ""),
                r.assigned_to.username if r.assigned_to else "Unassigned",
                (r.latest_message_ts or r.created_at).strftime("%Y-%m-%d %H:%M"),
                r.created_at.strftime("%Y-%m-%d"),
            ])
        return response

    queue_case = CaseExpression(
        When(status=ReportStatus.RESOLVED, then=Value("closed")),
        When(assigned_to__isnull=True, then=Value("new")),
        When(latest_message_sender=request.user.id, then=Value("waiting_on_student")),
        When(assigned_to=request.user, then=Value("assigned_to_me")),
        default=Value("assigned_to_me"),
        output_field=CharField(),
    )
    reports_qs = reports_qs.annotate(queue_state=queue_case)

    queue_priority = CaseExpression(
        When(queue_state="new", then=Value(0)),
        When(queue_state="assigned_to_me", then=Value(1)),
        When(queue_state="waiting_on_student", then=Value(2)),
        When(queue_state="closed", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    reports_qs = reports_qs.annotate(queue_priority=queue_priority)

    queue_counts_qs = reports_qs.values("queue_state").annotate(total=Count("id"))
    queue_counts = {row["queue_state"]: row["total"] for row in queue_counts_qs}

    metrics_qs = reports_qs
    queue_filter = request.GET.get("queue", "all")
    queue_metadata = {
        "new": {
            "label": "New",
            "description": "Unassigned reports/cases that no counselor has taken",
            "badge": "primary",
        },
        "assigned_to_me": {
            "label": "Assigned to Me",
            "description": "Reports currently being handled by you",
            "badge": "info",
        },
        "waiting_on_student": {
            "label": "Waiting on Student",
            "description": "Reports where you replied last and are waiting for student response",
            "badge": "warning",
        },
        "closed": {
            "label": "Closed",
            "description": "Completed, archived, or resolved reports",
            "badge": "success",
        },
    }

    if queue_filter and queue_filter != "all":
        reports_qs = reports_qs.filter(queue_state=queue_filter)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=assigned_reports.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Type", "Status", "Queue", "Assigned To", "Last Update", "Submitted"])
        for r in reports_qs:
            writer.writerow([
                r.id,
                r.get_incident_type_display(),
                r.get_status_display(),
                queue_metadata.get(r.queue_state, {}).get("label", ""),
                r.assigned_to.username if r.assigned_to else "Unassigned",
                (r.latest_message_ts or r.created_at).strftime("%Y-%m-%d %H:%M"),
                r.created_at.strftime("%Y-%m-%d"),
            ])
        return response
    
    now = timezone.now()
    current_window_start = now - timedelta(days=7)
    previous_window_start = now - timedelta(days=14)

    def build_trend(current_value, previous_value):
        change = current_value - previous_value
        if change > 0:
            icon = "fa-arrow-trend-up"
            color = "text-success"
        elif change < 0:
            icon = "fa-arrow-trend-down"
            color = "text-danger"
        else:
            icon = "fa-arrow-right-long"
            color = "text-muted"

        percent = None
        if previous_value:
            percent = round(abs(change) / previous_value * 100, 1)

        return {
            "change": change,
            "display_change": f"{change:+d}",
            "icon": icon,
            "color": color,
            "percent": percent,
            "label": "vs prev 7 days",
        }

    case_load_current = metrics_qs.filter(created_at__gte=current_window_start).count()
    case_load_previous = metrics_qs.filter(
        created_at__gte=previous_window_start,
        created_at__lt=current_window_start,
    ).count()

    messages_current = ChatMessage.objects.filter(
        recipient=request.user,
        timestamp__gte=current_window_start,
    ).count()
    messages_previous = ChatMessage.objects.filter(
        recipient=request.user,
        timestamp__gte=previous_window_start,
        timestamp__lt=current_window_start,
    ).count()

    appointments_current = metrics_qs.filter(
        support_needed=True,
        created_at__gte=current_window_start,
    ).count()
    appointments_previous = metrics_qs.filter(
        support_needed=True,
        created_at__gte=previous_window_start,
        created_at__lt=current_window_start,
    ).count()

    kpi_cards = [
        {
            "title": "Case Load (7d)",
            "value": case_load_current,
            "subtitle": "New reports entering your queue in the last 7 days",
            "icon": "fa-briefcase-medical",
            "trend": build_trend(case_load_current, case_load_previous),
        },
        {
            "title": "Messages Received (7d)",
            "value": messages_current,
            "subtitle": "Direct messages sent to you in the last 7 days",
            "icon": "fa-comments",
            "trend": build_trend(messages_current, messages_previous),
        },
        {
            "title": "Appointments Scheduled (7d)",
            "value": appointments_current,
            "subtitle": "Reports requesting support in the last 7 days",
            "icon": "fa-calendar-check",
            "trend": build_trend(appointments_current, appointments_previous),
        },
    ]
    
    reports_qs = reports_qs.order_by("queue_priority", "-last_activity", "-created_at")

    locations = reports_qs.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    paginator = Paginator(reports_qs, 25)
    page_number = request.GET.get("page")
    reports = paginator.get_page(page_number)
    
    for report in reports:
        meta = queue_metadata.get(report.queue_state, {
            "label": "Unknown",
            "badge": "secondary",
        })
        report.queue_label = meta["label"]
        report.queue_badge = meta["badge"]
        
        # SLA Hints: Calculate time-related metrics for priority indication
        now = timezone.now()
        
        # Calculate time deltas for overdue checking
        time_since_creation_delta = now - report.created_at
        
        # Time since last message or update
        if report.last_activity:
            time_since_last_activity_delta = now - report.last_activity
        else:
            time_since_last_activity_delta = now - report.created_at
        
        # Store the reference datetime for timesince template filter
        report.created_at_ref = report.created_at
        report.latest_activity_ref = report.last_activity or report.created_at
        
        # Check priority status based on time since activity
        if time_since_last_activity_delta > timedelta(hours=48):
            report.is_overdue = True
            report.overdue_badge = "danger"
            report.priority_level = "critical"
            report.priority_label = "🔴 Overdue (>48h)"
        elif time_since_last_activity_delta > timedelta(hours=24):
            report.is_overdue = False
            report.overdue_badge = "warning"
            report.priority_level = "medium"
            report.priority_label = "🟠 Needs Attention (>24h)"
        elif time_since_last_activity_delta > timedelta(hours=12):
            report.is_overdue = False
            report.overdue_badge = "info"
            report.priority_level = "normal"
            report.priority_label = "🟡 Recent (<24h)"
        else:
            report.is_overdue = False
            report.overdue_badge = "success"
            report.priority_level = "low"
            report.priority_label = "🟢 Active (<12h)"

    queue_summary = [
        {
            "value": key,
            "label": meta["label"],
            "description": meta["description"],
            "badge": meta["badge"],
            "count": queue_counts.get(key, 0),
        }
        for key, meta in queue_metadata.items()
    ]
    
    # Count overdue reports (48+ hours without activity)
    now = timezone.now()
    overdue_count = 0
    for report in reports:
        if hasattr(report, 'is_overdue') and report.is_overdue:
            overdue_count += 1
    
    context = {
        "reports": reports,
        "kpi_cards": kpi_cards,
        "statuses": ReportStatus.choices,
        "locations": locations,
        "queue_summary": queue_summary,
        "queue_filter": queue_filter,
        "queue_metadata": queue_metadata,
        "overdue_count": overdue_count,
    }
    return render(request, "counselor_dashboard.html", context)

@auth_login_required
@auth_user_passes_test(_is_counselor)
def my_cases(request):
    """List the cases claimed by the logged-in counselor."""

    base_qs = (
        Report.objects.filter(assigned_to=request.user)
        .select_related("reporter")
    )

    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "").strip()

    reports_qs = base_qs

    if status_filter:
        reports_qs = reports_qs.filter(status=status_filter)

    if search_query:
        if search_query.isdigit():
            reports_qs = reports_qs.filter(id=int(search_query))
        else:
            reports_qs = reports_qs.filter(
                Q(reporter__username__icontains=search_query)
                | Q(reporter_name__icontains=search_query)
            )

    latest_message = (
        ChatMessage.objects.filter(report=OuterRef("pk"))
        .order_by("-timestamp")
    )

    reports_qs = reports_qs.annotate(
        latest_message_ts=Subquery(latest_message.values("timestamp")[:1]),
        has_unread=Exists(
            ChatMessage.objects.filter(
                report=OuterRef("pk"),
                recipient=request.user,
                is_read=False,
            )
        ),
    last_activity=Coalesce("latest_message_ts", "updated_at", "created_at"),
    ).order_by("-last_activity", "-created_at")

    reports = list(reports_qs)

    for report in reports:
        report.last_activity = report.last_activity or report.created_at

    status_counts = {
        row["status"]: row["total"]
        for row in base_qs.order_by().values("status").annotate(total=Count("id"))
    }

    status_summary = [
        {
            "value": value,
            "label": label,
            "count": status_counts.get(value, 0),
        }
        for value, label in ReportStatus.choices
    ]

    context = {
        "reports": reports,
        "statuses": ReportStatus.choices,
        "status_summary": status_summary,
        "total_cases": base_qs.count(),
        "status_filter": status_filter,
        "search_query": search_query,
        "has_filters": bool(status_filter or search_query),
    }

    return render(request, "counselor_my_cases.html", context)

@auth_login_required
@auth_user_passes_test(_is_counselor)
def case_detail(request, report_id):
    report = get_object_or_404(
        Report,
        Q(id=report_id)
        & (Q(assigned_to=request.user) | Q(assigned_to__isnull=True)),
    )
    
    if request.method == "GET":
        # Record that the counselor accessed the report detail view.
        AuditLogMixin.log_view(
            user=request.user,
            obj=report,
            metadata={
                "action": SystemLog.ActionType.VIEWED,
                "report_id": report.pk,
                "path": request.path,
            },
            description=f"{request.user.get_full_name() or request.user.username} viewed Report #{report.pk}",
        )
        
    is_owner = report.assigned_to_id == request.user.id
    note_form = CaseNoteForm(request.POST or None)
    msg_form = MessageForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if "add_note" in request.POST and is_owner and note_form.is_valid():
            try:
                note = CaseNote.objects.create(
                    report=report,
                    counselor=request.user,
                    note=note_form.cleaned_data["note"],
                )
            except OperationalError:
                messages.error(
                    request,
                    "Unable to save your note because the notes table is missing required columns."
                    " Please contact an administrator to run the latest database migrations.",
                )
            else:
                # Capture edits made by counselors via case notes.
                AuditLogMixin.log_edit(
                    user=request.user,
                    obj=report,
                    metadata={
                        "action": "add_note",
                        "note_id": note.pk,
                    },
                    description=f"{request.user.get_full_name() or request.user.username} added a note to Report #{report.pk}",
                )
                return redirect("counselor_case_detail", report_id=report.id)
        
        if "resolve_case" in request.POST and is_owner:
            report.status = ReportStatus.RESOLVED
            report.resolved_at = timezone.now()
            report.awaiting_response = False
            report.save(update_fields=["status", "awaiting_response"])
            # Document the closure event for the report.
            AuditLogMixin.log_close(
                user=request.user,
                obj=report,
                metadata={
                    "action": "resolve_case",
                    "report_id": report.pk,
                },
                description=f"{request.user.get_full_name() or request.user.username} closed Report #{report.pk}",
            )
            admins = get_user_model().objects.filter(is_superuser=True)
            admin_emails = admins.values_list("email", flat=True)
            if admin_emails:
                try:
                    last_msg = (
                        ChatMessage.objects.filter(
                            report=report, sender=request.user
                        )
                        .order_by("-timestamp")
                        .first()
                    )
                except OperationalError:
                    last_msg = None
                body = f"Counselor {request.user.username} marked report #{report.id} as resolved."
                if last_msg:
                    body += (
                        "\n\nLast message to student:\n"
                        f"{last_msg.get_body_for(request.user)}"
                    )
                send_mail(
                    subject=f"Report #{report.id} resolved",
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=list(admin_emails),
                    fail_silently=True,
                )
                for admin in admins:
                    AdminAlert.objects.create(
                        admin=admin,
                        report=report,
                        message=last_msg.get_body_for(request.user) if last_msg else "",
                    )
            return redirect("counselor_case_detail", report_id=report.id)
        
        if (
            "send_msg" in request.POST
            and is_owner
            and msg_form.is_valid()
            and report.reporter
        ):
            parent_id = msg_form.cleaned_data.get("parent_id")
            parent = ChatMessage.objects.filter(id=parent_id, report=report).first() if parent_id else None
            message = ChatMessage.create(
                report=report,
                sender=request.user,
                recipient=report.reporter,
                message=msg_form.cleaned_data["message"],
                parent=parent,
                attachment=msg_form.cleaned_data.get("attachment"),
            )
            Report.objects.filter(pk=report.pk).update(awaiting_response=False)
            # Sending a message modifies the report workflow, so log it as an edit.
            AuditLogMixin.log_edit(
                user=request.user,
                obj=report,
                metadata={
                    "action": "send_message",
                    "message_id": message.pk,
                },
                description=f"{request.user.get_full_name() or request.user.username} messaged the reporter on Report #{report.pk}",
            )
            return redirect("counselor_case_detail", report_id=report.id)

    try:
        # Evaluate the queryset immediately so missing columns raise inside the try block.
        notes = list(
            CaseNote.objects.filter(report=report).order_by("-created_at")
        )
    except OperationalError:
        notes = []
        messages.error(
            request,
            "Counseling notes could not be loaded because the notes table is missing a required column."
            " Please ask an administrator to apply the latest migrations.",
        )
    ChatMessage.objects.filter(report=report, recipient=request.user, is_read=False).update(is_read=True)
    try:
        ChatMessage.objects.filter(report=report, recipient=request.user, is_read=False).update(is_read=True)
        chat_messages = (
            ChatMessage.objects.filter(report=report, parent__isnull=True)
            .select_related("sender")
            .prefetch_related("replies__sender")
        )
    except OperationalError:
        chat_messages = []
    
    latest_student_message = ""
    suggested_replies = []
    emotion_timeline = []
    emotion_counts = Counter()
    critical_alerts = 0
    elevated_alerts = 0
    if report.reporter:
        try:
            latest_incoming = (
                ChatMessage.objects.filter(report=report, sender=report.reporter)
                .order_by("-timestamp")
                .first()
            )
        except OperationalError:
            latest_incoming = None
        if latest_incoming:
            try:
                latest_student_message = latest_incoming.get_body_for(request.user)
            except Exception as exc:  # pragma: no cover - encryption edge cases
                logger.warning("Unable to decrypt latest student message", exc_info=exc)
                latest_student_message = ""
            if latest_student_message:
                suggested_replies = generate_suggested_replies(latest_student_message)

        student_messages = (
            ChatMessage.objects.filter(report=report, sender=report.reporter)
            .order_by("timestamp")
        )
        for msg in student_messages:
            entry = {
                "timestamp": msg.timestamp,
                "label": msg.emotion,
                "label_display": msg.get_emotion_display(),
                "risk": msg.risk_level,
                "risk_display": msg.get_risk_level_display(),
                "confidence": round(msg.emotion_confidence * 100),
                "confidence_raw": msg.emotion_confidence,
                "score": msg.emotion_score,
                "explanation": msg.emotion_explanation,
            }
            if not entry["explanation"]:
                entry["explanation"] = "AI could not detect strong emotional cues."
            emotion_timeline.append(entry)
            emotion_counts[msg.emotion] += 1
            if msg.risk_level == RiskLevel.CRITICAL:
                critical_alerts += 1
            elif msg.risk_level == RiskLevel.ELEVATED:
                elevated_alerts += 1

    latest_emotion = emotion_timeline[-1] if emotion_timeline else None
    recent_scores = [entry["score"] for entry in emotion_timeline[-3:]]
    trend_direction = "steady"
    if len(recent_scores) >= 2:
        delta = recent_scores[-1] - recent_scores[0]
        if delta > 0.1:
            trend_direction = "improving"
        elif delta < -0.1:
            trend_direction = "declining"

    emotion_distribution = [
        {
            "key": key,
            "label": EmotionLabel(key).label if key in EmotionLabel.values else key.title(),
            "count": count,
        }
        for key, count in emotion_counts.most_common()
    ]

    emotion_overview = {
        "timeline": emotion_timeline[-10:],
        "latest": latest_emotion,
        "distribution": emotion_distribution,
        "critical_count": critical_alerts,
        "elevated_count": elevated_alerts,
        "trend_direction": trend_direction,
    }

    
    context = {
        "report": report,
        "notes": notes,
        "chat_messages": chat_messages,
        "note_form": note_form,
        "msg_form": msg_form,
        "suggested_replies": suggested_replies,
        "latest_student_message": latest_student_message,
        "emotion_overview": emotion_overview,
        "timeline_events": report.timeline_events(),
        "is_owner": is_owner,
    }
    return render(request, "counselor_case_detail.html", context)


@auth_login_required
@auth_user_passes_test(_is_counselor)
def messages_view(request):
    """List message threads for the counselor, grouped by report."""
    q = request.GET.get("q", "").strip()
    conversation_count = 0
    thread_groups = []
    try:
        thread_qs = (
            ChatMessage.objects.filter(
                Q(sender=request.user) | Q(recipient=request.user), parent__isnull=True
            )
            .select_related("report", "sender", "recipient")
            .prefetch_related("replies__sender", "replies__recipient")
            .order_by("-timestamp")
        )
        if q:
            if q.isdigit():
                thread_qs = thread_qs.filter(report__id=q)
            else:
                thread_qs = thread_qs.none()

        ChatMessage.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )

        threads = list(thread_qs)
        conversation_count = len(threads)
        grouped = {}
        for thread in threads:
            replies = list(thread.replies.all())
            last_msg = replies[-1] if replies else thread
            thread.last_message = last_msg

            sender = getattr(last_msg, "sender", None)
            sender_name = ""
            if sender:
                sender_name = sender.get_full_name() or sender.username or ""
            thread.last_sender_name = sender_name or "Unknown sender"

            group = grouped.setdefault(
                thread.report_id,
                {
                    "report": thread.report,
                    "threads": [],
                    "last_message": None,
                    "last_sender_name": "",
                },
            )
            group["threads"].append(thread)

            if last_msg and (
                group["last_message"] is None
                or last_msg.timestamp > group["last_message"].timestamp
            ):
                group["last_message"] = last_msg
                group["last_sender_name"] = thread.last_sender_name

        for group in grouped.values():
            if group["last_message"] is None and group["threads"]:
                fallback_thread = group["threads"][0]
                group["last_message"] = fallback_thread.last_message or fallback_thread
                group["last_sender_name"] = fallback_thread.last_sender_name

        thread_groups = sorted(grouped.values(), key=lambda g: g["report"].id)
    except OperationalError:
        conversation_count = 0
        thread_groups = []

    context = {
        "thread_groups": thread_groups,
        "q": q,
        "conversation_count": conversation_count,
        "threads": threads if 'threads' in locals() else [],
    }
    return render(request, "counselor_messages.html", context)


@auth_login_required
@auth_user_passes_test(_is_counselor)
def claim_case(request, report_id):
    """Allow a counselor to claim an unassigned case."""
    report = get_object_or_404(Report, id=report_id, assigned_to__isnull=True)
    
    if request.method == "POST":
        report.assigned_to = request.user
        report.status = ReportStatus.UNDER_REVIEW
        report.assigned_at = timezone.now()
        report.resolved_at = None
        report.save()
        
        AuditLogMixin.log_edit(
            user=request.user,
            obj=report,
            metadata={
                "action": "claim_case",
                "report_id": report.pk,
            },
            description=f"{request.user.get_full_name() or request.user.username} claimed Report #{report.pk}",
        )
        
        messages.success(request, f"Successfully claimed Report #{report.id}")
        return redirect("counselor_case_detail", report_id=report.id)
    
    return redirect("counselor_dashboard")


@auth_login_required
@auth_user_passes_test(_is_counselor)
def analytics_dashboard(request):
    """Analytics dashboard showing counselor performance metrics with Plotly charts."""
    # Get time range from query parameter (7, 30, or all)
    time_range = request.GET.get('range', '30')
    
    # Base queryset with time filtering
    reports_qs = Report.objects.filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    )
    
    if time_range != 'all':
        cutoff = timezone.now() - timedelta(days=int(time_range))
        reports_qs = reports_qs.filter(created_at__gte=cutoff)
    
    now = timezone.now()
    
    latest_message = (
        ChatMessage.objects.filter(report=OuterRef("pk"))
        .order_by("-timestamp")
    )

    reports_qs = reports_qs.annotate(
        latest_message_ts=Subquery(latest_message.values("timestamp")[:1]),
        latest_message_sender=Subquery(latest_message.values("sender")[:1]),
    )

    queue_case = CaseExpression(
        When(status=ReportStatus.RESOLVED, then=Value("closed")),
        When(assigned_to__isnull=True, then=Value("new")),
        When(latest_message_sender=request.user.id, then=Value("waiting_on_student")),
        When(assigned_to=request.user, then=Value("assigned_to_me")),
        default=Value("assigned_to_me"),
        output_field=CharField(),
    )

    reports_qs = reports_qs.annotate(queue_state=queue_case)
    
    # KPI Calculations
    # 1. Total cases handled
    total_cases = reports_qs.count()
    
    # 2. Pending cases count
    pending_count = reports_qs.filter(status=ReportStatus.PENDING).count()
    
    # 3. Average closure time (for resolved reports)
    resolved_reports = reports_qs.filter(status=ReportStatus.RESOLVED)
    avg_closure_days = 0
    if resolved_reports.exists():
        closure_times = []
        for report in resolved_reports:
            if report.updated_at and report.created_at:
                delta = report.updated_at - report.created_at
                closure_times.append(delta.total_seconds() / 86400)  # Convert to days
        if closure_times:
            avg_closure_days = sum(closure_times) / len(closure_times)
    
    # 4. Average response time (time from report creation to first counselor message)
    avg_response_hours = 0
    response_times = []
    try:
        for report in reports_qs:
            # Find first message sent by a counselor (not the reporter)
            first_message = ChatMessage.objects.filter(report=report).exclude(sender=report.reporter).order_by('timestamp').first()
            
            if first_message and report.created_at:
                delta = first_message.timestamp - report.created_at
                response_times.append(delta.total_seconds() / 3600)  # Convert to hours
    except (OperationalError, AttributeError):
        pass
    
    if response_times:
        avg_response_hours = sum(response_times) / len(response_times)
    
    # Chart Data
    # 1. Reports per week
    weekly_reports = (
        reports_qs.annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )
    
    weekly_chart_data = {
        'x': [str(item['week']) for item in weekly_reports],
        'y': [item['count'] for item in weekly_reports],
    }
    
    # 2. Reports per month (for toggled view)
    monthly_reports = (
        reports_qs.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    monthly_chart_data = {
        'x': [str(item['month']) for item in monthly_reports],
        'y': [item['count'] for item in monthly_reports],
    }

    # 3. Reports by status
    status_data = reports_qs.values('status').annotate(count=Count('id'))
    status_chart_data = {
        'labels': [item['status'].replace('_', ' ').title() for item in status_data],
        'values': [item['count'] for item in status_data],
    }
    
     # 3. Reports by incident type
    incident_data = reports_qs.values('incident_type').annotate(count=Count('id'))
    incident_chart_data = {
        'labels': [item['incident_type'].replace('_', ' ').title() for item in incident_data],
        'values': [item['count'] for item in incident_data],
    }
    
    # 5. Pipeline (status by queue)
    queue_metadata = {
        'new': {
            'label': 'New',
            'badge': 'primary',
        },
        'assigned_to_me': {
            'label': 'Assigned to Me',
            'badge': 'info',
        },
        'waiting_on_student': {
            'label': 'Waiting on Student',
            'badge': 'warning',
        },
        'closed': {
            'label': 'Closed',
            'badge': 'success',
        },
    }

    status_label_map = dict(ReportStatus.choices)
    queue_order = ['new', 'assigned_to_me', 'waiting_on_student', 'closed']
    status_order = [choice[0] for choice in ReportStatus.choices]

    pipeline_counts = (
        reports_qs.values('queue_state', 'status')
        .annotate(total=Count('id'))
    )

    pipeline_matrix = {
        status: {queue: 0 for queue in queue_order}
        for status in status_order
    }

    for row in pipeline_counts:
        queue_key = row['queue_state'] or 'assigned_to_me'
        status_key = row['status']
        if status_key in pipeline_matrix and queue_key in pipeline_matrix[status_key]:
            pipeline_matrix[status_key][queue_key] = row['total']

    pipeline_series = []
    for status in status_order:
        values = [pipeline_matrix[status][queue] for queue in queue_order]
        if any(values):
            pipeline_series.append({
                'name': status_label_map.get(status, status.replace('_', ' ').title()),
                'values': values,
            })

    pipeline_chart_data = {
        'queues': [queue_metadata[q]['label'] for q in queue_order],
        'series': pipeline_series,
    }

    # 6. Queue distribution (donut chart)
    queue_totals = reports_qs.values('queue_state').annotate(total=Count('id'))
    queue_totals_map = {row['queue_state']: row['total'] for row in queue_totals}
    queue_chart_data = {
        'labels': [queue_metadata[q]['label'] for q in queue_order],
        'values': [queue_totals_map.get(q, 0) for q in queue_order],
    }
    
    claimed_cases_count = queue_totals_map.get('assigned_to_me', 0)
    unassigned_queue_count = queue_totals_map.get('new', 0)

    try:
        unread_messages_count = ChatMessage.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
    except OperationalError:
        unread_messages_count = 0

    recently_closed_cutoff = now - timedelta(days=7)
    recently_closed_count = resolved_reports.filter(
        updated_at__gte=recently_closed_cutoff
    ).count()

    reports_list = list(reports_qs)

    sla_buckets = {
        '<12h': 0,
        '12-24h': 0,
        '24-48h': 0,
        '>48h': 0,
    }

    for report in reports_list:
        last_activity = report.latest_message_ts or report.updated_at or report.created_at
        if not last_activity:
            continue
        hours_open = (now - last_activity).total_seconds() / 3600
        if hours_open < 12:
            sla_buckets['<12h'] += 1
        elif hours_open < 24:
            sla_buckets['12-24h'] += 1
        elif hours_open < 48:
            sla_buckets['24-48h'] += 1
        else:
            sla_buckets['>48h'] += 1

    total_sla = sum(sla_buckets.values()) or 1
    sla_compliance = ((sla_buckets['<12h'] + sla_buckets['12-24h']) / total_sla) * 100

    sla_chart_data = {
        'buckets': list(sla_buckets.keys()),
        'counts': list(sla_buckets.values()),
        'score': round(sla_compliance, 1),
    }

    portal_summary_cards = [
        {
            'title': 'My Claimed Cases',
            'count': claimed_cases_count,
            'description': 'Active reports that you are currently shepherding.',
            'url': reverse('counselor_my_cases'),
            'icon': 'fa-user-check',
            'badge_variant': 'info',
            'badge_label': 'In Progress',
        },
        {
            'title': 'Unassigned Queue',
            'count': unassigned_queue_count,
            'description': 'Reports waiting to be claimed from the shared counselor queue.',
            'url': reverse('counselor_dashboard'),
            'icon': 'fa-inbox',
            'badge_variant': 'warning',
            'badge_label': 'Needs Claim',
        },
        {
            'title': 'Unread Messages',
            'count': unread_messages_count,
            'description': 'New student replies or admin notes that need your response.',
            'url': reverse('counselor_messages'),
            'icon': 'fa-comments',
            'badge_variant': 'danger',
            'badge_label': 'New Replies',
        },
        {
            'title': 'Recently Closed',
            'count': recently_closed_count,
            'description': 'Cases resolved in the past week to celebrate and review.',
            'url': reverse('counselor_analytics'),
            'icon': 'fa-chart-line',
            'badge_variant': 'success',
            'badge_label': 'This Week',
        },
    ]

    
    context = {
        'total_cases': total_cases,
        'pending_count': pending_count,
        'avg_closure_days': round(avg_closure_days, 1),
        'avg_response_hours': round(avg_response_hours, 1),
        'weekly_chart': json.dumps(weekly_chart_data),
        'monthly_chart': json.dumps(monthly_chart_data),
        'status_chart': json.dumps(status_chart_data),
        'incident_chart': json.dumps(incident_chart_data),
        'queue_chart': json.dumps(queue_chart_data),
        'pipeline_chart': json.dumps(pipeline_chart_data),
        'sla_chart': json.dumps(sla_chart_data),
        'time_range': time_range,
        'portal_summary_cards': portal_summary_cards,
        'claimed_cases_count': claimed_cases_count,
        'unassigned_queue_count': unassigned_queue_count,
        'unread_messages_count': unread_messages_count,
        'recently_closed_count': recently_closed_count,
    }
    
    return render(request, 'counselor_analytics.html', context)

@auth_login_required
@auth_user_passes_test(_is_counselor)
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.full_name and request.user.get_full_name():
        profile.full_name = request.user.get_full_name()
    profile.set_role("Counselor")

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was updated.")
            return redirect("counselor_profile")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile, user=request.user)

    open_cases = (
        Report.objects.filter(assigned_to=request.user)
        .exclude(status=ReportStatus.RESOLVED)
        .count()
    )

    recent_notes = CaseNote.objects.filter(
        counselor=request.user,
        created_at__gte=timezone.now() - timedelta(days=7),
    ).count()

    response_deltas = []
    counselor_messages = (
        ChatMessage.objects.filter(sender=request.user)
        .order_by('-timestamp')[:20]
    )

    for message in counselor_messages:
        previous = (
            ChatMessage.objects.filter(
                report=message.report,
                timestamp__lt=message.timestamp,
            )
            .exclude(sender=request.user)
            .order_by('-timestamp')
            .first()
        )
        if previous:
            response_deltas.append(message.timestamp - previous.timestamp)

    avg_response_time = None
    if response_deltas:
        total_delta = sum(response_deltas, timedelta())
        average_delta = total_delta / len(response_deltas)
        total_seconds = int(average_delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes and not days:
            parts.append(f"{minutes}m")
        avg_response_time = " ".join(parts) or "<1m"

    profile_schedule_url = getattr(profile, "schedule_url", "")
    profile_reports_url = getattr(profile, "reports_url", "")
    profile_messages_url = getattr(profile, "messages_url", "")
    
    counselor_profile = CounselorProfile.objects.filter(user=request.user).first()
    specialization_tags = []
    if counselor_profile:
        specialization_display = counselor_profile.get_specialization_display()
        specialization_tags = [specialization_display]
        setattr(profile, "specializations", specialization_display)

    schedule_url = _safe_reverse("counselor_dashboard")
    if schedule_url == "#":
        schedule_url = profile_schedule_url or "#"

    reports_url = _safe_reverse("counselor_my_cases")
    if reports_url == "#":
        reports_url = profile_reports_url or "#"

    messages_url = _safe_reverse("counselor_messages")
    if messages_url == "#":
        messages_url = profile_messages_url or "#"
    
    # Ensure template fallbacks always have concrete values without raising lookups.
    fallback_attributes = {
        "schedule_url": schedule_url,
        "reports_url": reports_url,
        "messages_url": messages_url,
        "open_cases": open_cases,
        "upcoming_sessions": recent_notes,
        "avg_response_time": avg_response_time or "",
        "specialization_tags": specialization_tags,
    }
    for attr_name, attr_value in fallback_attributes.items():
        if not getattr(profile, attr_name, None):
            setattr(profile, attr_name, attr_value)

    context = {
        "profile": profile,
        "user": request.user,
        "can_edit": True,
        "is_counselor": True,
        "open_cases": open_cases,
        "upcoming_sessions": recent_notes,
        "avg_response_time": avg_response_time,
        "schedule_url": schedule_url,
        "reports_url": reports_url,
        "messages_url": messages_url,
        "specialization_tags": specialization_tags,
        "form": form,
        "default_avatar": static("images/default-avatar.svg"),
    }

    context.update(build_two_factor_context(request.user))

    return render(request, "counselor_portal/profile.html", context)