from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.core.cache import caches
from django.core.paginator import Paginator
from django.db import OperationalError, ProgrammingError
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import NoReverseMatch, reverse
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods, require_POST
import datetime as dt
import logging
from datetime import time, timedelta
from io import BytesIO, StringIO
import json
import zipfile

# Use the project's default cache backend for storing dashboard statistics
cache = caches["default"]
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
import csv
from django.contrib.contenttypes.models import ContentType
from tccweb.core.models import (
    Report,
    EducationalResource,
    ReportType,
    ReportStatus,
    SystemLog,
    SecurityLog,
)
from tccweb.core.forms import EducationalResourceForm, QuizForm, QuizQuestionFormSet
from tccweb.accounts.forms import ProfileForm
from tccweb.accounts.models import Profile
from tccweb.counselor_portal.models import CaseNote, ChatMessage
from .forms import CounselorCreationForm, ImpersonationForm, DataExportForm

logger = logging.getLogger(__name__)

try:
    from tccweb.core.models import Quiz  # or wherever your Quiz model is
except ImportError:
    Quiz = None

def _safe_reverse(name: str, *args, **kwargs) -> str:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"

def _client_ip(request) -> str | None:
    """Best-effort extraction of the requester IP address."""

    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def _impersonation_redirect_for(user: User) -> str:
    """Return the most appropriate landing page for the impersonated account."""

    if user.is_superuser:
        return _safe_reverse("admin_dashboard")
    if user.is_staff:
        counselor_home = _safe_reverse("counselor_dashboard")
        if counselor_home != "#":
            return counselor_home
    user_dashboard = _safe_reverse("dashboard")
    if user_dashboard != "#":
        return user_dashboard
    return _safe_reverse("index")

def _start_of_day(value):
    """Return a timezone-aware datetime for the start of the provided date."""

    if not value:
        return None
    combined = dt.datetime.combine(value, time.min)
    return timezone.make_aware(combined) if timezone.is_naive(combined) else combined


def _end_of_day(value):
    """Return a timezone-aware datetime for the end of the provided date."""

    if not value:
        return None
    combined = dt.datetime.combine(value, time.max)
    return timezone.make_aware(combined) if timezone.is_naive(combined) else combined


def _format_datetime(value):
    """Render datetimes in ISO-8601 format for downstream compliance tools."""

    if not value:
        return ""
    try:
        return timezone.localtime(value).isoformat()
    except (ValueError, TypeError):  # pragma: no cover
        return str(value)


def _json_dump(value):
    """Serialize JSON metadata as a compact string for CSV exports."""

    if value in (None, ""):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    total_reports = Report.objects.count()
    resolved_reports = Report.objects.filter(status=ReportStatus.RESOLVED).count()
    pending_reports = Report.objects.filter(status=ReportStatus.PENDING).count()
    under_review_reports = Report.objects.filter(status=ReportStatus.UNDER_REVIEW).count()

    resolution_rate = int(round((resolved_reports / total_reports) * 100)) if total_reports else 0

    recent_reports = (
        Report.objects.select_related("assigned_to", "reporter")
        .order_by("-created_at")[:10]
    )

    monthly_stats = cache.get("dashboard_monthly_stats")
    if monthly_stats is None:
        monthly_qs = (
            Report.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        monthly_stats = [
            {"month": m["month"].strftime("%Y-%m"), "count": m["count"]}
            for m in monthly_qs
        ]
        cache.set("dashboard_monthly_stats", monthly_stats, 300)

    type_stats = cache.get("dashboard_type_stats") or []
    if not type_stats:
        type_qs = (
            Report.objects.values("incident_type")
            .annotate(count=Count("id")).order_by("-count")
        )
        type_stats = [
            {"type": r["incident_type"], "count": r["count"]}
            for r in type_qs
        ]
        cache.set("dashboard_type_stats", type_stats, 300)

    ctx = {
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "pending_reports": pending_reports,
        "under_review_reports": under_review_reports,
        "resolution_rate": resolution_rate,
        "recent_reports": recent_reports,
        "monthly_stats": monthly_stats,
        "type_stats": type_stats,
    }
    return render(request, 'admin_dashboard.html', ctx)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_reports(request):
    reports = Report.objects.select_related("reporter", "assigned_to").all()
    incident_type = request.GET.get("type")
    status = request.GET.get("status")
    start = request.GET.get("start")
    end = request.GET.get("end")
    if incident_type:
        reports = reports.filter(incident_type=incident_type)
    if status:
        reports = reports.filter(status=status)
    if start:
        reports = reports.filter(created_at__date__gte=start)
    if end:
        reports = reports.filter(created_at__date__lte=end)
    
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=reports.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Type", "Status", "Reporter", "Submitted"])
        for r in reports:
            reporter = "Anonymous" if r.is_anonymous else (r.reporter.username if r.reporter else "")
            writer.writerow([
                r.id,
                r.get_incident_type_display(),
                r.status,
                reporter,
                r.created_at.strftime("%Y-%m-%d"),
            ])
        return response

    locations = reports.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    
    paginator = Paginator(reports, 25)
    page_number = request.GET.get("page")
    reports_page = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    
    ctx = {
        "reports": reports_page,
        "types": ReportType.choices,
        "statuses": ReportStatus.choices,
        "locations": locations,
        "params": params.urlencode(),
    }
    return render(request, "admin_reports.html", ctx)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_data_exports(request):
    """Allow administrators to build compliance-friendly export bundles."""

    default_initial = {
        "start_date": timezone.now().date() - timedelta(days=30),
        "end_date": timezone.now().date(),
        "statuses": [choice[0] for choice in ReportStatus.choices],
    }

    if request.method == "POST":
        form = DataExportForm(request.POST)
    else:
        form = DataExportForm(initial=default_initial)

    status_labels = dict(ReportStatus.choices)
    status_breakdown = [
        {
            "value": row["status"],
            "label": status_labels.get(row["status"], row["status"]),
            "count": row["count"],
        }
        for row in Report.objects.values("status").annotate(count=Count("id")).order_by("status")
    ]

    now = timezone.now()
    recent_threshold = now - timedelta(days=30)
    report_stats = {
        "total_reports": Report.objects.count(),
        "open_cases": Report.objects.exclude(status=ReportStatus.RESOLVED).count(),
        "recent_reports": Report.objects.filter(created_at__gte=recent_threshold).count(),
        "case_notes": CaseNote.objects.count(),
        "messages": ChatMessage.objects.count(),
    }

    if request.method == "POST" and form.is_valid():
        cleaned = form.cleaned_data
        start_dt = _start_of_day(cleaned.get("start_date"))
        end_dt = _end_of_day(cleaned.get("end_date"))
        statuses = cleaned.get("statuses") or []

        report_qs = Report.objects.select_related("reporter", "assigned_to").order_by("id")
        if start_dt:
            report_qs = report_qs.filter(created_at__gte=start_dt)
        if end_dt:
            report_qs = report_qs.filter(created_at__lte=end_dt)
        if statuses:
            report_qs = report_qs.filter(status__in=statuses)

        reports_list = list(report_qs)
        report_ids = [report.id for report in reports_list]

        include_case_notes = cleaned.get("include_case_notes")
        include_messages = cleaned.get("include_messages")
        include_system_logs = cleaned.get("include_system_logs")
        include_security_logs = cleaned.get("include_security_logs")

        case_notes_list = []
        if include_case_notes and report_ids:
            notes_qs = CaseNote.objects.select_related("counselor").filter(report_id__in=report_ids)
            if start_dt:
                notes_qs = notes_qs.filter(created_at__gte=start_dt)
            if end_dt:
                notes_qs = notes_qs.filter(created_at__lte=end_dt)
            case_notes_list = list(notes_qs.order_by("created_at"))

        messages_list = []
        if include_messages and report_ids:
            messages_qs = ChatMessage.objects.select_related("sender", "recipient").filter(report_id__in=report_ids)
            if start_dt:
                messages_qs = messages_qs.filter(timestamp__gte=start_dt)
            if end_dt:
                messages_qs = messages_qs.filter(timestamp__lte=end_dt)
            messages_list = list(messages_qs.order_by("timestamp"))

        system_logs_list = []
        if include_system_logs and report_ids:
            report_ct = ContentType.objects.get_for_model(Report)
            system_logs_qs = SystemLog.objects.select_related("user").filter(
                content_type=report_ct,
                object_id__in=report_ids,
            )
            if start_dt:
                system_logs_qs = system_logs_qs.filter(timestamp__gte=start_dt)
            if end_dt:
                system_logs_qs = system_logs_qs.filter(timestamp__lte=end_dt)
            system_logs_list = list(system_logs_qs.order_by("timestamp"))

        security_logs_list = []
        if include_security_logs:
            security_logs_qs = SecurityLog.objects.select_related("actor", "target_user").all()
            if start_dt:
                security_logs_qs = security_logs_qs.filter(timestamp__gte=start_dt)
            if end_dt:
                security_logs_qs = security_logs_qs.filter(timestamp__lte=end_dt)
            security_logs_list = list(security_logs_qs.order_by("timestamp"))

        export_format = cleaned.get("export_format")
        generated_at = timezone.now()
        buffer = BytesIO()

        reports_payload = []
        for report in reports_list:
            reporter_user = report.reporter if report.reporter and not report.is_anonymous else None
            assigned = report.assigned_to
            reports_payload.append(
                {
                    "id": report.id,
                    "tracking_code": report.tracking_code,
                    "incident_type": report.incident_type,
                    "incident_type_label": report.get_incident_type_display(),
                    "status": report.status,
                    "status_label": report.get_status_display(),
                    "created_at": _format_datetime(report.created_at),
                    "updated_at": _format_datetime(report.updated_at),
                    "incident_date": _format_datetime(report.incident_date),
                    "resolved_at": _format_datetime(report.resolved_at),
                    "assigned_at": _format_datetime(report.assigned_at),
                    "reporter_username": reporter_user.get_username() if reporter_user else None,
                    "reporter_full_name": reporter_user.get_full_name() if reporter_user else report.reporter_name,
                    "reporter_email": reporter_user.email if reporter_user else report.reporter_email,
                    "reporter_phone": report.reporter_phone,
                    "is_anonymous": report.is_anonymous,
                    "location": report.location,
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "witness_present": report.witness_present,
                    "previous_incidents": report.previous_incidents,
                    "support_needed": report.support_needed,
                    "awaiting_response": report.awaiting_response,
                    "assigned_counselor_username": assigned.get_username() if assigned else None,
                    "assigned_counselor_full_name": assigned.get_full_name() if assigned else None,
                    "description": report.description,
                    "counselor_notes": report.counselor_notes,
                }
            )

        case_notes_payload = [
            {
                "id": note.id,
                "report_id": note.report_id,
                "counselor_username": note.counselor.get_username(),
                "counselor_full_name": note.counselor.get_full_name(),
                "note": note.note,
                "created_at": _format_datetime(note.created_at),
            }
            for note in case_notes_list
        ]

        messages_payload = [
            {
                "id": message.id,
                "report_id": message.report_id,
                "timestamp": _format_datetime(message.timestamp),
                "sender": message.sender.get_username(),
                "recipient": message.recipient.get_username(),
                "parent_id": message.parent_id,
                "is_read": message.is_read,
                "attachment": message.attachment.name if message.attachment else "",
                "cipher_for_sender": message.cipher_for_sender,
                "cipher_for_recipient": message.cipher_for_recipient,
                "emotion": message.emotion,
                "emotion_label": message.get_emotion_display(),
                "emotion_score": message.emotion_score,
                "emotion_confidence": message.emotion_confidence,
                "risk_level": message.risk_level,
                "risk_label": message.get_risk_level_display(),
                "emotion_explanation": message.emotion_explanation,
            }
            for message in messages_list
        ]

        system_logs_payload = [
            {
                "id": log.id,
                "timestamp": _format_datetime(log.timestamp),
                "action_type": log.action_type,
                "action_label": log.get_action_type_display(),
                "actor_username": log.user.get_username() if log.user else None,
                "actor_full_name": log.user.get_full_name() if log.user else None,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "description": log.description,
                "metadata": log.metadata,
            }
            for log in system_logs_list
        ]

        security_logs_payload = [
            {
                "id": log.id,
                "timestamp": _format_datetime(log.timestamp),
                "event_type": log.event_type,
                "event_label": log.get_event_type_display(),
                "actor_username": log.actor.get_username() if log.actor else None,
                "actor_full_name": log.actor.get_full_name() if log.actor else None,
                "target_username": log.target_user.get_username() if log.target_user else None,
                "target_full_name": log.target_user.get_full_name() if log.target_user else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "description": log.description,
                "metadata": log.metadata,
            }
            for log in security_logs_list
        ]

        def write_csv(filename, headers, rows):
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
            archive.writestr(filename, output.getvalue())

        def write_json(filename, payload):
            archive.writestr(
                filename,
                json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            )

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            metadata_payload = {
                "generated_at": _format_datetime(generated_at),
                "generated_by": request.user.get_username(),
                "filters": {
                    "start_date": cleaned.get("start_date").isoformat() if cleaned.get("start_date") else None,
                    "end_date": cleaned.get("end_date").isoformat() if cleaned.get("end_date") else None,
                    "statuses": statuses or "ALL",
                    "include_case_notes": include_case_notes,
                    "include_messages": include_messages,
                    "include_system_logs": include_system_logs,
                    "include_security_logs": include_security_logs,
                    "export_format": export_format,
                },
                "counts": {
                    "reports": len(reports_payload),
                    "case_notes": len(case_notes_payload),
                    "messages": len(messages_payload),
                    "system_logs": len(system_logs_payload),
                    "security_logs": len(security_logs_payload),
                },
                "version": "1.0",
            }
            archive.writestr(
                "metadata.json",
                json.dumps(metadata_payload, indent=2, ensure_ascii=False, default=str),
            )

            if export_format == "csv":
                write_csv(
                    "reports.csv",
                    [
                        "ID",
                        "Tracking code",
                        "Incident type",
                        "Incident label",
                        "Status",
                        "Status label",
                        "Created at",
                        "Updated at",
                        "Incident date",
                        "Resolved at",
                        "Assigned at",
                        "Reporter username",
                        "Reporter full name",
                        "Reporter email",
                        "Reporter phone",
                        "Anonymous",
                        "Location",
                        "Latitude",
                        "Longitude",
                        "Witness present",
                        "Previous incidents",
                        "Support needed",
                        "Awaiting response",
                        "Assigned counselor username",
                        "Assigned counselor full name",
                        "Description",
                        "Counselor notes",
                    ],
                    [
                        [
                            item["id"],
                            item["tracking_code"],
                            item["incident_type"],
                            item["incident_type_label"],
                            item["status"],
                            item["status_label"],
                            item["created_at"],
                            item["updated_at"],
                            item["incident_date"],
                            item["resolved_at"],
                            item["assigned_at"],
                            item["reporter_username"],
                            item["reporter_full_name"],
                            item["reporter_email"],
                            item["reporter_phone"],
                            item["is_anonymous"],
                            item["location"],
                            item["latitude"],
                            item["longitude"],
                            item["witness_present"],
                            item["previous_incidents"],
                            item["support_needed"],
                            item["awaiting_response"],
                            item["assigned_counselor_username"],
                            item["assigned_counselor_full_name"],
                            item["description"],
                            item["counselor_notes"],
                        ]
                        for item in reports_payload
                    ],
                )
            else:
                write_json("reports.json", reports_payload)

            if include_case_notes:
                if export_format == "csv":
                    write_csv(
                        "case_notes.csv",
                        [
                            "ID",
                            "Report ID",
                            "Counselor username",
                            "Counselor full name",
                            "Created at",
                            "Note",
                        ],
                        [
                            [
                                item["id"],
                                item["report_id"],
                                item["counselor_username"],
                                item["counselor_full_name"],
                                item["created_at"],
                                item["note"],
                            ]
                            for item in case_notes_payload
                        ],
                    )
                else:
                    write_json("case_notes.json", case_notes_payload)

            if include_messages:
                if export_format == "csv":
                    write_csv(
                        "messages.csv",
                        [
                            "ID",
                            "Report ID",
                            "Timestamp",
                            "Sender",
                            "Recipient",
                            "Parent ID",
                            "Read",
                            "Attachment",
                            "Cipher for sender",
                            "Cipher for recipient",
                            "Emotion",
                            "Emotion label",
                            "Emotion score",
                            "Emotion confidence",
                            "Risk level",
                            "Risk label",
                            "Emotion explanation",
                        ],
                        [
                            [
                                item["id"],
                                item["report_id"],
                                item["timestamp"],
                                item["sender"],
                                item["recipient"],
                                item["parent_id"],
                                item["is_read"],
                                item["attachment"],
                                item["cipher_for_sender"],
                                item["cipher_for_recipient"],
                                item["emotion"],
                                item["emotion_label"],
                                item["emotion_score"],
                                item["emotion_confidence"],
                                item["risk_level"],
                                item["risk_label"],
                                item["emotion_explanation"],
                            ]
                            for item in messages_payload
                        ],
                    )
                else:
                    write_json("messages.json", messages_payload)

            if include_system_logs:
                if export_format == "csv":
                    write_csv(
                        "system_logs.csv",
                        [
                            "ID",
                            "Timestamp",
                            "Action",
                            "Action label",
                            "Actor username",
                            "Actor full name",
                            "Object type",
                            "Object ID",
                            "Description",
                            "Metadata",
                        ],
                        [
                            [
                                item["id"],
                                item["timestamp"],
                                item["action_type"],
                                item["action_label"],
                                item["actor_username"],
                                item["actor_full_name"],
                                item["object_type"],
                                item["object_id"],
                                item["description"],
                                _json_dump(item["metadata"]),
                            ]
                            for item in system_logs_payload
                        ],
                    )
                else:
                    write_json("system_logs.json", system_logs_payload)

            if include_security_logs:
                if export_format == "csv":
                    write_csv(
                        "security_logs.csv",
                        [
                            "ID",
                            "Timestamp",
                            "Event",
                            "Event label",
                            "Actor username",
                            "Actor full name",
                            "Target username",
                            "Target full name",
                            "IP address",
                            "User agent",
                            "Description",
                            "Metadata",
                        ],
                        [
                            [
                                item["id"],
                                item["timestamp"],
                                item["event_type"],
                                item["event_label"],
                                item["actor_username"],
                                item["actor_full_name"],
                                item["target_username"],
                                item["target_full_name"],
                                item["ip_address"],
                                item["user_agent"],
                                item["description"],
                                _json_dump(item["metadata"]),
                            ]
                            for item in security_logs_payload
                        ],
                    )
                else:
                    write_json("security_logs.json", security_logs_payload)

        buffer.seek(0)
        filename = f"compliance_export_{generated_at.strftime('%Y%m%d_%H%M%S')}.zip"
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    context = {
        "form": form,
        "status_breakdown": status_breakdown,
        "report_stats": report_stats,
    }
    return render(request, "admin_portal/data_exports.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_case_assignment(request):
    reports = Report.objects.select_related('assigned_to', 'reporter').all()
    users = User.objects.filter(is_staff=True)
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        assigned_to = request.POST.get('assigned_to')
        status = request.POST.get('status')
        notes = request.POST.get('notes')
        report = get_object_or_404(Report, id=report_id)
        previous_assignee = report.assigned_to_id
        previous_status = report.status
        report.assigned_to_id = assigned_to or None
        if report.assigned_to_id and report.assigned_to_id != previous_assignee:
            report.assigned_at = timezone.now()
        elif not report.assigned_to_id:
            report.assigned_at = None
        if status:
            report.status = status
            if status == ReportStatus.RESOLVED:
                if previous_status != ReportStatus.RESOLVED:
                    report.resolved_at = timezone.now()
            elif previous_status == ReportStatus.RESOLVED:
                report.resolved_at = None
        if notes is not None:
            report.counselor_notes = notes
        report.save()
        messages.success(request, 'Report updated.')
        return redirect('admin_case_assignment')
    return render(
        request,
        'admin_case_assignment.html',
        {'reports': reports, 'users': users, 'statuses': ReportStatus.choices},
    )

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_analytics(request):
    monthly_stats = cache.get("dashboard_monthly_stats")
    if monthly_stats is None:
        monthly_qs = (
            Report.objects
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        monthly_stats = [
            {'month': m['month'].strftime('%Y-%m'), 'count': m['count']} for m in monthly_qs
        ]
        cache.set("dashboard_monthly_stats", monthly_stats, 300)

    type_stats = cache.get("dashboard_type_stats") or []
    if not type_stats:
        type_qs = (
            Report.objects.values('incident_type')
            .annotate(count=Count('id')).order_by('-count')
        )
        type_stats = [
            {'type': r['incident_type'], 'count': r['count']} for r in type_qs
        ]
        cache.set("dashboard_type_stats", type_stats, 300)

    locations = Report.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    return render(
        request,
        'admin_analytics.html',
        {'monthly_stats': monthly_stats, 'type_stats': type_stats, 'reports': locations},
    )

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_awareness(request):
    try:
        resource_qs = EducationalResource.objects.all().select_related("created_by").order_by('-created_at')
    except Exception:
        logger.exception("Failed to load educational resources")
        resource_qs = EducationalResource.objects.none()
        messages.error(request, "Resources unavailable.")
        
    resource_paginator = Paginator(resource_qs, 10)
    resource_page_number = request.GET.get('resource_page')
    resources = resource_paginator.get_page(resource_page_number)

    if Quiz:
        try:
            quiz_qs = Quiz.objects.all().prefetch_related('questions').order_by('-created_at')
        except Exception:
            logger.exception("Failed to load quizzes")
            quiz_qs = Quiz.objects.none()
            messages.error(request, "Quizzes unavailable.")
    else:
        quiz_qs = []
        messages.warning(request, "Quiz functionality is unavailable.")
        
    quiz_paginator = Paginator(quiz_qs, 10)
    quiz_page_number = request.GET.get('quiz_page')
    quizzes = quiz_paginator.get_page(quiz_page_number)

    # default forms
    form = EducationalResourceForm()
    if Quiz:
        quiz_form = QuizForm()
        question_formset = QuizQuestionFormSet(prefix='questions')
    else:
        quiz_form = None
        question_formset = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'resource':
            form = EducationalResourceForm(request.POST, request.FILES)
            if form.is_valid():
                res = form.save(commit=False)
                if not getattr(res, 'created_by_id', None):
                    res.created_by = request.user
                res.save()
                messages.success(request, 'Resource added.')
                return redirect('admin_awareness')
            else:
                error_msg = form.errors.get('file', ['Upload failed.'])[0]
                messages.error(request, error_msg)

        elif form_type == 'quiz' and Quiz:
            quiz_form = QuizForm(request.POST)
            question_formset = QuizQuestionFormSet(request.POST, prefix='questions')
            if quiz_form.is_valid() and question_formset.is_valid():
                quiz = quiz_form.save(commit=False)
                if not getattr(quiz, 'created_by_id', None):
                    quiz.created_by = request.user
                quiz.save()
                question_formset.instance = quiz
                question_formset.save()
                messages.success(request, 'Quiz created.')
                return redirect('admin_awareness')
            else:
                messages.error(request, 'Quiz submission failed. Please correct the errors below.')
        elif form_type == 'quiz':
            messages.error(request, 'Quiz functionality is unavailable.')
            
    context = {
        'form': form,
        'resources': resources,
        'quiz_form': quiz_form,
        'question_formset': question_formset,
        'quizzes': quizzes,
    }
    return render(request, 'admin_awareness.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_resource(request, pk):
    resource = get_object_or_404(EducationalResource, pk=pk)
    if request.method == "POST":
        resource.delete()
        messages.success(request, "Resource deleted.")
    return redirect("admin_awareness")

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_management(request):
    counselors = User.objects.filter(is_staff=True, is_superuser=False).order_by('username')
    students = User.objects.filter(is_staff=False).order_by('username')
    form = CounselorCreationForm()
    
    if request.method == 'POST':
        if request.POST.get('form_type') == 'create':
            form = CounselorCreationForm(request.POST)
            if form.is_valid():
                new_counselor = form.save()
                SecurityLog.objects.create(
                    actor=request.user,
                    target_user=new_counselor,
                    event_type=SecurityLog.EventType.PERMISSION_GRANTED,
                    ip_address=_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    description=(
                        f"{request.user.get_username()} created counselor "
                        f"account {new_counselor.get_username()}."
                    ),
                    metadata={
                        "action": "create_counselor",
                        "target_user_id": new_counselor.pk,
                    },
                )
                messages.success(request, 'Counselor account created.')
                return redirect('admin_user_management')
        else:
            uid = request.POST.get('user_id')
            action = request.POST.get('action')
            target = get_object_or_404(User, id=uid)
            event_type = None
            description = None
            if action == 'approve' and not target.is_staff:
                target.is_staff = True
                event_type = SecurityLog.EventType.PERMISSION_GRANTED
                description = (
                    f"{request.user.get_username()} granted counselor access to "
                    f"{target.get_username()}."
                )
            elif action == 'revoke' and target.is_staff:
                target.is_staff = False
                event_type = SecurityLog.EventType.PERMISSION_REVOKED
                description = (
                    f"{request.user.get_username()} revoked counselor access from "
                    f"{target.get_username()}."
                )

            if event_type:
                target.save(update_fields=["is_staff"])
                SecurityLog.objects.create(
                    actor=request.user,
                    target_user=target,
                    event_type=event_type,
                    ip_address=_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    description=description,
                    metadata={
                        "action": action,
                        "target_user_id": target.pk,
                    },
                )
            else:
                target.save(update_fields=["is_staff"])
            messages.success(request, 'User updated.')
            return redirect('admin_user_management')
    return render(
        request,
        'admin_user_management.html',
        {'counselors': counselors, 'students': students, 'form': form},
    )
    
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_profile(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.full_name and user.get_full_name():
        profile.full_name = user.get_full_name()
    profile.set_role("Administrator")

    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
            user=user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was updated.")
            return redirect("admin_profile")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile, user=user)

    active_users = User.objects.filter(is_active=True).count()
    open_alerts = Report.objects.exclude(status=ReportStatus.RESOLVED).count()
    last_backup_at = timezone.localtime(timezone.now()).strftime("%b %d, %Y %I:%M %p")

    context = {
        "profile": profile,
        "user": user,
        "can_edit": True,
        "is_admin": True,
        "admin_dashboard_url": _safe_reverse("admin_dashboard"),
        "impersonate_url": _safe_reverse("admin_impersonate_user"),
        "security_logs_url": _safe_reverse("admin_security_logs"),
        "data_export_url": _safe_reverse("admin_data_exports"),
        "data_export_url": _safe_reverse("admin_reports"),
        "user_management_url": _safe_reverse("admin_user_management"),
        "reports_overview_url": _safe_reverse("admin_reports"),
        "system_settings_url": _safe_reverse("admin_dashboard"),
        "refresh_caches_url": "#",
        "active_users": active_users,
        "open_alerts": open_alerts,
        "last_backup_at": last_backup_at,
        "form": form,
        "default_avatar": static("images/default-avatar.svg"),
    }

    return render(request, "admin_portal/profile.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_security_logs(request):
    """Display authentication and permission changes for review."""

    event_filter = request.GET.get("event", "")
    search_query = (request.GET.get("q") or "").strip()
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")

    recent_rows = [
        (label, 0) for value, label in SecurityLog.EventType.choices
    ]

    try:
        logs = SecurityLog.objects.select_related("actor", "target_user")
        if event_filter and event_filter in dict(SecurityLog.EventType.choices):
            logs = logs.filter(event_type=event_filter)

        if search_query:
            logs = logs.filter(
                Q(actor__username__icontains=search_query)
                | Q(actor__email__icontains=search_query)
                | Q(target_user__username__icontains=search_query)
                | Q(target_user__email__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        start_date = parse_date(start) if start else None
        if start_date:
            logs = logs.filter(timestamp__date__gte=start_date)

        end_date = parse_date(end) if end else None
        if end_date:
            logs = logs.filter(timestamp__date__lte=end_date)

        logs = logs.order_by("-timestamp")

        paginator = Paginator(logs, 50)
        page_obj = paginator.get_page(request.GET.get("page"))

        recent_window = timezone.now() - timedelta(days=7)
        recent_totals = (
            SecurityLog.objects.filter(timestamp__gte=recent_window)
            .values("event_type")
            .annotate(total=Count("id"))
        )
        recent_summary = {row["event_type"]: row["total"] for row in recent_totals}

        recent_rows = [
            (label, recent_summary.get(value, 0))
            for value, label in SecurityLog.EventType.choices
        ]

        total_logs = SecurityLog.objects.count()

    except (OperationalError, ProgrammingError):
        messages.error(
            request,
            "Security logs are unavailable until database migrations are applied.",
        )
        empty_paginator = Paginator([], 50)
        page_obj = empty_paginator.get_page(1)
        total_logs = 0

    context = {
        "logs": page_obj,
        "event_choices": SecurityLog.EventType.choices,
        "filters": {
            "event": event_filter,
            "q": search_query,
            "start": start,
            "end": end,
        },
        "has_filters": any([event_filter, search_query, start, end]),
        "recent_rows": recent_rows,
        "total_logs": total_logs,
    }

    return render(request, "admin_portal/security_logs.html", context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "POST"])
def admin_impersonate_user(request):
    """Allow administrators to temporarily act as another account."""

    search_source = request.POST if request.method == "POST" else request.GET
    search_query = (search_source.get("q") or "").strip()
    next_url = search_source.get("next", "")

    candidate_queryset = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
    )
    if search_query:
        candidate_queryset = candidate_queryset.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )
    candidate_queryset = candidate_queryset.order_by("username")

    form = ImpersonationForm(
        request.POST or None,
        current_user=request.user,
        user_queryset=candidate_queryset,
    )

    has_candidates = candidate_queryset.exists()
    preview_limit = 25
    preview_users = list(candidate_queryset[:preview_limit])

    if request.method == "POST" and form.is_valid():
        target_user = form.cleaned_data["user"]
        backend = request.session.get(
            "_auth_user_backend",
            "django.contrib.auth.backends.ModelBackend",
        )
        original_id = request.user.pk
        original_name = request.user.get_full_name() or request.user.get_username()

        login(request, target_user, backend=backend)

        request.session["impersonator_id"] = original_id
        request.session["impersonator_name"] = original_name
        request.session["impersonator_backend"] = backend
        request.session["is_impersonating"] = True
        request.session["impersonation_started_at"] = timezone.now().isoformat()

        destination = request.POST.get("next") or next_url or _impersonation_redirect_for(target_user)
        messages.success(
            request,
            f"You are now impersonating {target_user.get_full_name() or target_user.get_username()}.",
        )
        logger.info(
            "Administrator %s (id=%s) started impersonating user %s (id=%s)",
            original_name,
            original_id,
            target_user.get_username(),
            target_user.pk,
        )
        return redirect(destination or _safe_reverse("index"))

    context = {
        "form": form,
        "search_query": search_query,
        "has_candidates": has_candidates,
        "preview_users": preview_users,
        "next_url": next_url,
        "preview_limit": preview_limit,
    }

    return render(request, "admin_portal/impersonate_user.html", context)


@login_required
@require_POST
def admin_stop_impersonation(request):
    """Return the current session to the original administrator account."""

    impersonator_id = request.session.get("impersonator_id")
    next_url = request.POST.get("next") or _safe_reverse("admin_profile")

    if not impersonator_id:
        messages.info(request, "No active impersonation session was found.")
        return redirect(next_url or _safe_reverse("index"))

    try:
        original_user = User.objects.get(pk=impersonator_id)
    except User.DoesNotExist:
        for key in [
            "impersonator_id",
            "impersonator_name",
            "impersonator_backend",
            "is_impersonating",
            "impersonation_started_at",
        ]:
            request.session.pop(key, None)
        messages.error(
            request,
            "We could not restore your administrator session. Please sign in again.",
        )
        return redirect(_safe_reverse("account_login"))

    backend = request.session.get(
        "impersonator_backend",
        request.session.get(
            "_auth_user_backend",
            "django.contrib.auth.backends.ModelBackend",
        ),
    )

    login(request, original_user, backend=backend)

    for key in [
        "impersonator_id",
        "impersonator_name",
        "impersonator_backend",
        "is_impersonating",
        "impersonation_started_at",
    ]:
        request.session.pop(key, None)

    messages.success(request, "You have returned to your administrator account.")
    logger.info(
        "Administrator id=%s stopped impersonation and returned to their account.",
        original_user.pk,
    )

    return redirect(next_url or _safe_reverse("admin_profile"))