from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
import csv


from tccweb.core.models import Report, ReportStatus  # provides status choices for filtering
from .forms import CaseNoteForm
from tccweb.core.forms import MessageForm
from .models import CaseNote, ChatMessage, AdminAlert


def _is_counselor(user):
    return user.is_staff or getattr(getattr(user, "profile", None), "is_staff", False)


def counselor_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not _is_counselor(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


@counselor_required
def dashboard(request):
    reports = (
        Report.objects.filter(assigned_to=request.user)
        .select_related("reporter", "assigned_to")
    )
    status = request.GET.get("status")
    start = request.GET.get("start")
    end = request.GET.get("end")
    if status:
        reports = reports.filter(status=status)
    if start:
        reports = reports.filter(created_at__date__gte=start)
    if end:
        reports = reports.filter(created_at__date__lte=end)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=assigned_reports.csv"
        writer = csv.writer(response)
        writer.writerow(["ID", "Type", "Status", "Submitted"])
        for r in reports:
            writer.writerow([
                r.id,
                r.get_incident_type_display(),
                r.get_status_display(),
                r.created_at.strftime("%Y-%m-%d"),
            ])
        return response
    
    stats = reports.values("status").annotate(total=Count("id"))
    locations = reports.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    context = {
        "reports": reports,
        "stats": stats,
        "statuses": ReportStatus.choices,
        "locations": locations,
    }
    return render(request, "counselor_dashboard.html", context)


@counselor_required
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


@counselor_required
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

