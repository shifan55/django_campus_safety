from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import (
    Avg,
    Case,
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
from django.db.models.functions import TruncWeek, TruncMonth
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
import csv
import json


from tccweb.core.models import Report, ReportStatus  # provides status choices for filtering
from .forms import CaseNoteForm
from tccweb.core.forms import MessageForm
from .models import CaseNote, ChatMessage, AdminAlert


def _is_counselor(user):
    return user.is_staff or getattr(getattr(user, "profile", None), "is_staff", False)


@login_required
@user_passes_test(_is_counselor)
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

    queue_case = Case(
        When(status=ReportStatus.RESOLVED, then=Value("closed")),
        When(assigned_to__isnull=True, then=Value("new")),
        When(latest_message_sender=request.user.id, then=Value("waiting_on_student")),
        When(assigned_to=request.user, then=Value("assigned_to_me")),
        default=Value("assigned_to_me"),
        output_field=CharField(),
    )
    reports_qs = reports_qs.annotate(queue_state=queue_case)

    queue_priority = Case(
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
    
    reports_qs = reports_qs.order_by("queue_priority", "-latest_message_ts", "-created_at")

    stats = (
        reports_qs.order_by()
        .values("status")
        .annotate(total=Count("id"))
    )
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
        if report.latest_message_ts:
            time_since_last_activity_delta = now - report.latest_message_ts
        else:
            time_since_last_activity_delta = now - report.created_at
        
        # Store the reference datetime for timesince template filter
        report.created_at_ref = report.created_at
        report.latest_activity_ref = report.latest_message_ts if report.latest_message_ts else report.created_at
        
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
        "stats": stats,
        "statuses": ReportStatus.choices,
        "locations": locations,
        "queue_summary": queue_summary,
        "queue_filter": queue_filter,
        "queue_metadata": queue_metadata,
        "overdue_count": overdue_count,
    }
    return render(request, "counselor_dashboard.html", context)

@login_required
@user_passes_test(_is_counselor)
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
    ).order_by("-latest_message_ts", "-updated_at", "-created_at")

    reports = list(reports_qs)

    for report in reports:
        report.last_activity = (
            report.latest_message_ts or report.updated_at or report.created_at
        )

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

@login_required
@user_passes_test(_is_counselor)
def case_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id, assigned_to=request.user)
    note_form = CaseNoteForm(request.POST or None)
    msg_form = MessageForm(request.POST or None)

    if request.method == "POST":
        if "add_note" in request.POST and note_form.is_valid():
            CaseNote.objects.create(
                report=report,
                counselor=request.user,
                note=note_form.cleaned_data["note"],
            )
            return redirect("counselor_case_detail", report_id=report.id)
        
        if "resolve_case" in request.POST:
            report.status = ReportStatus.RESOLVED
            report.save()
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
        
        if "send_msg" in request.POST and msg_form.is_valid() and report.reporter:
            parent_id = msg_form.cleaned_data.get("parent_id")
            parent = ChatMessage.objects.filter(id=parent_id, report=report).first() if parent_id else None
            ChatMessage.create(
                report=report,
                sender=request.user,
                recipient=report.reporter,
                message=msg_form.cleaned_data["message"],
                parent=parent,
            )
            return redirect("counselor_case_detail", report_id=report.id)

    notes = CaseNote.objects.filter(report=report).order_by("-created_at")
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
    
    context = {
        "report": report,
        "notes": notes,
        "chat_messages": chat_messages,
        "note_form": note_form,
        "msg_form": msg_form,
    }
    return render(request, "counselor_case_detail.html", context)


@login_required
@user_passes_test(_is_counselor)
def messages_view(request):
    """List message threads for the counselor, grouped by report."""
    q = request.GET.get("q", "").strip()
    try:
        threads = (
            ChatMessage.objects.filter(
                Q(sender=request.user) | Q(recipient=request.user), parent__isnull=True
            )
            .select_related("report", "sender", "recipient")
            .prefetch_related("replies__sender", "replies__recipient")
            .order_by("-timestamp")
        )
        if q:
            if q.isdigit():
                threads = threads.filter(report__id=q)
            else:
                threads = threads.none()
        ChatMessage.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    except OperationalError:
        threads = []
    return render(
        request, "counselor_messages.html", {"threads": threads, "q": q}
    )


@login_required
@user_passes_test(_is_counselor)
def claim_case(request, report_id):
    """Allow a counselor to claim an unassigned case."""
    report = get_object_or_404(Report, id=report_id, assigned_to__isnull=True)
    
    if request.method == "POST":
        report.assigned_to = request.user
        report.status = ReportStatus.UNDER_REVIEW
        report.save()
        
        messages.success(request, f"Successfully claimed Report #{report.id}")
        return redirect("counselor_case_detail", report_id=report.id)
    
    return redirect("counselor_dashboard")


@login_required
@user_passes_test(_is_counselor)
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
    weekly_reports = reports_qs.annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(count=Count('id')).order_by('week')
    
    weekly_chart_data = {
        'x': [str(item['week']) for item in weekly_reports],
        'y': [item['count'] for item in weekly_reports],
    }
    
    # 2. Reports by status
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
    
    # 4. Queue distribution
    assigned_count = reports_qs.filter(assigned_to=request.user).count()
    unassigned_count = reports_qs.filter(assigned_to__isnull=True).count()
    queue_chart_data = {
        'labels': ['Assigned to Me', 'Unassigned'],
        'values': [assigned_count, unassigned_count],
    }
    
    context = {
        'total_cases': total_cases,
        'pending_count': pending_count,
        'avg_closure_days': round(avg_closure_days, 1),
        'avg_response_hours': round(avg_response_hours, 1),
        'weekly_chart': json.dumps(weekly_chart_data),
        'status_chart': json.dumps(status_chart_data),
        'incident_chart': json.dumps(incident_chart_data),
        'queue_chart': json.dumps(queue_chart_data),
        'time_range': time_range,
    }
    
    return render(request, 'counselor_analytics.html', context)

