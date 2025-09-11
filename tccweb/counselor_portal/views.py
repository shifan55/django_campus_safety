from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from tccweb.core.models import Report
from .forms import CaseNoteForm, MessageForm
from .models import CaseNote, ChatMessage


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
    reports = Report.objects.filter(assigned_to=request.user)
    stats = reports.values("status").annotate(total=Count("id"))
    return render(request, "counselor_dashboard.html", {"reports": reports, "stats": stats})


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
        if "send_msg" in request.POST and msg_form.is_valid() and report.reporter:
            ChatMessage.objects.create(
                report=report,
                sender=request.user,
                recipient=report.reporter,
                message=msg_form.cleaned_data["message"],
            )
            return redirect("counselor_case_detail", report_id=report.id)

    notes = CaseNote.objects.filter(report=report).order_by("-created_at")
    messages = ChatMessage.objects.filter(report=report)
    context = {
        "report": report,
        "notes": notes,
        "messages": messages,
        "note_form": note_form,
        "msg_form": msg_form,
    }
    return render(request, "counselor_case_detail.html", context)


@counselor_required
def messages_view(request):
    msgs = ChatMessage.objects.filter(
        recipient=request.user
    ).select_related("report", "sender").order_by("-timestamp")
    return render(request, "counselor_messages.html", {"messages": msgs})