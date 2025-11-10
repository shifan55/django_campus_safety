from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.urls import NoReverseMatch, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from tccweb.core.models import Report, EducationalResource, SupportContact
from tccweb.core.forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm, MessageForm
from tccweb.counselor_portal.emotion import analyze_emotion
from tccweb.counselor_portal.models import ChatMessage, RiskLevel
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def _safe_reverse(name: str, *args, **kwargs) -> str:
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"

def _notify_counselor_new_message(report, sender, insight=None):
    """Send a websocket notification to the assigned counselor."""

    if sender.is_staff or not report.assigned_to_id:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    sender_name = sender.get_full_name() or sender.username
    title = f"\ud83d\udd14 New message in Case #{report.id}"
    icon = "🔔"
    body = f"{sender_name} sent a new message."
    variant = "info"

    if insight:
        if insight.risk_level == RiskLevel.CRITICAL:
            title = f"🔴 Critical alert in Case #{report.id}"
            icon = "🔴"
            variant = "critical"
        elif insight.risk_level == RiskLevel.ELEVATED:
            title = f"🟠 Sensitive update in Case #{report.id}"
            icon = "🟠"
            variant = "elevated"
        if insight.label and insight.label != "neutral":
            body += f" Detected tone: {insight.display_label}."

    async_to_sync(channel_layer.group_send)(
        f"user_{report.assigned_to_id}",
        {
            "type": "notify",
            "data": {
                "title": title,
                "body": body,
                "url": reverse("counselor_case_detail", args=[report.id]),
                "icon": icon,
                "variant": variant,
            },
        },
    )

def index(request):
    try:
        recent_resources = (
            EducationalResource.objects.filter(is_public=True)
            .select_related("created_by")
            .order_by("-created_at")[:3]
        )
    except Exception:
        logger.exception("Failed to load recent resources")
        recent_resources = []
        messages.error(request, "Unable to load recent resources.")

    context = {
        "recent_resources": recent_resources,
    }
    return render(request, "index.html", context)


def awareness(request):
    try:
        resources = (
            EducationalResource.objects.filter(is_public=True)
            .select_related("created_by")
        )
    except Exception:
        logger.exception("Failed to load resources")
        resources = EducationalResource.objects.none()
        messages.error(request, "Unable to load resources.")

    category = request.GET.get('category')
    resource_type = request.GET.get('type')
    query = request.GET.get('q')
    sort = request.GET.get('sort', '-created_at')

    if category and category != 'all':
        resources = resources.filter(category=category)
    if resource_type and resource_type != 'all':
        resources = resources.filter(resource_type=resource_type)
    if query:
        resources = resources.filter(Q(title__icontains=query) | Q(content__icontains=query))

    allowed_sorts = ['title', '-title', 'created_at', '-created_at']
    if sort not in allowed_sorts:
        sort = '-created_at'
    resources = resources.order_by(sort)

    paginator = Paginator(resources, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    try:
        contacts_qs = SupportContact.objects.filter(is_available=True).order_by('name')
    except Exception:
        logger.exception("Failed to load support contacts")
        contacts_qs = SupportContact.objects.none()
        messages.error(request, "Unable to load support contacts.")
        
    contacts_paginator = Paginator(contacts_qs, 6)
    contacts_page_number = request.GET.get('contact_page')
    contacts_page = contacts_paginator.get_page(contacts_page_number)
    context = {
        'resources': page_obj,
        'contacts': contacts_page,
        'category': category or 'all',
        'type': resource_type or 'all',
        'query': query or '',
        'sort': sort,
    }
    return render(request, 'awareness.html', context)

@require_GET
def resource_detail(request, resource_id):
    """AJAX endpoint returning details for a single public resource."""
    resource = get_object_or_404(EducationalResource, id=resource_id, is_public=True)
    data = {
        "id": resource.id,
        "title": resource.title,
        "content": resource.content,
        "resource_type": resource.resource_type,
    }
    if resource.url:
        data["url"] = resource.url
    if resource.file:
        data["file"] = resource.file.url
    return JsonResponse(data)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                if user.is_staff:
                    return redirect('admin_dashboard')
                return redirect('index')
            messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Registration successful. You can now log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def report_anonymous(request):
    if request.method == 'POST':
        form = AnonymousReportForm(request.POST)
    else:
        form = AnonymousReportForm()
    context = {
        'form': form,
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }
    if request.method == 'POST':
        if form.is_valid():
            report = Report.objects.create(
                incident_type=form.cleaned_data['incident_type'],
                description=form.cleaned_data['description'],
                incident_date=form.cleaned_data['incident_date'],
                location=form.cleaned_data.get('location', ''),
                latitude=form.cleaned_data.get('latitude'),
                longitude=form.cleaned_data.get('longitude'),
                reporter_name=form.cleaned_data.get('reporter_name', ''),
                reporter_email=form.cleaned_data.get('reporter_email', ''),
                reporter_phone=form.cleaned_data.get('reporter_phone', ''),
                is_anonymous=True,
                awaiting_response=True,
            )
            messages.success(request, 'Report submitted successfully.')
            return redirect('report_success', tracking_code=report.tracking_code)
    return render(request, 'report_anonymous.html', context)


@login_required
@user_passes_test(lambda u: not u.is_staff)
def dashboard(request):
    query = request.GET.get('q')
    sort = request.GET.get('sort', '-created_at')

    try:
        reports_qs = Report.objects.select_related("reporter", "assigned_to").filter(
            reporter=request.user
        )
    except Exception:
        logger.exception("Failed to load user reports")
        reports_qs = Report.objects.none()
        messages.error(request, "Unable to load your reports.")

    if query:
        reports_qs = reports_qs.filter(description__icontains=query)

    allowed_sorts = ['incident_type', 'status', 'created_at', '-created_at']
    if sort not in allowed_sorts:
        sort = '-created_at'
    reports_qs = reports_qs.order_by(sort)

    paginator = Paginator(reports_qs, 10)
    page_number = request.GET.get('page')
    user_reports = paginator.get_page(page_number)

    context = {
        'user_reports': user_reports,
        'query': query or '',
        'sort': sort,
    }
    return render(request, 'dashboard.html', context)


@login_required
@user_passes_test(lambda u: not u.is_staff)
def submit_report(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            if form.cleaned_data.get('is_anonymous'):
                report.reporter = None
            else:
                report.reporter = request.user
            report.is_anonymous = form.cleaned_data.get('is_anonymous')
            report.awaiting_response = True
            report.save()
            messages.success(request, 'Report submitted successfully.')
            return redirect('report_success', tracking_code=report.tracking_code)
    else:
        initial = {
            'reporter_name': request.user.get_full_name() or request.user.username,
            'reporter_email': request.user.email,
        }
        if hasattr(request.user, 'profile'):
            initial['reporter_phone'] = getattr(request.user.profile, 'phone', '')
        form = ReportForm(initial=initial)
    return render(request, 'submit_report.html', {'form': form})


def track_report(request):
    report = None
    if request.method == 'POST':
        code = request.POST.get('tracking_code', '').strip()
        try:
            report = Report.objects.get(tracking_code=code)
        except Report.DoesNotExist:
            messages.error(request, 'No report found with that tracking code.')
    return render(request, 'track_report.html', {'report': report})

@login_required
@user_passes_test(lambda u: not u.is_staff)
def report_messages(request, report_id):
    report = get_object_or_404(Report, id=report_id, reporter=request.user)
    msg_form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and msg_form.is_valid() and report.assigned_to:
        parent_id = msg_form.cleaned_data.get("parent_id")
        parent = ChatMessage.objects.filter(id=parent_id, report=report).first() if parent_id else None
        prior_context = []
        for history in (
            ChatMessage.objects.filter(report=report, sender=request.user)
            .order_by("-timestamp")[:5]
        ):
            try:
                prior_context.append(history.get_body_for(request.user))
            except Exception:  # pragma: no cover - encryption edge cases
                continue
        prior_context.reverse()

        insight = analyze_emotion(
            msg_form.cleaned_data["message"],
            context=prior_context,
        )
        
        ChatMessage.create(
            report=report,
            sender=request.user,
            recipient=report.assigned_to,
            message=msg_form.cleaned_data["message"],
            parent=parent,
            attachment=msg_form.cleaned_data.get("attachment"),
            emotion_insight=insight,
        )
        Report.objects.filter(pk=report.pk).update(awaiting_response=True)
        _notify_counselor_new_message(report, request.user, insight)
        return redirect("report_messages", report_id=report.id)
    ChatMessage.objects.filter(report=report, recipient=request.user, is_read=False).update(is_read=True)
    chat_messages = (
        ChatMessage.objects.filter(report=report, parent__isnull=True)
        .select_related("sender")
        .prefetch_related("replies__sender")
    )
    context = {
        "report": report,
        "chat_messages": chat_messages,
        "msg_form": msg_form,
        "timeline_events": report.timeline_events(),
    }

    return render(request, "report_messages.html", context)

@login_required
@user_passes_test(lambda u: not u.is_staff)
def user_messages(request):
    """List conversation threads for the logged-in user."""
    q = request.GET.get("q", "").strip()
    threads_qs = (
        ChatMessage.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user), parent__isnull=True
        )
        .select_related("sender", "recipient", "report")
        .prefetch_related("replies__sender", "replies__recipient")
        .order_by("-timestamp")
    )
    if q:
        if q.isdigit():
            threads_qs = threads_qs.filter(report__id=q)
        else:
            threads_qs = threads_qs.none()
    
    threads = list(threads_qs)
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

    context = {
        "thread_groups": thread_groups,
        "q": q,
        "conversation_count": len(threads),
        "threads": threads,
    }
    return render(request, "user_messages.html", context)


def report_success(request, tracking_code):
    return render(request, 'report_success.html', {'tracking_code': tracking_code})


@login_required
def profile_view(request):
    if request.user.is_superuser:
        return redirect('admin_profile')
    if request.user.is_staff:
        return redirect('counselor_profile')

    profile = getattr(request.user, "profile", None)
    linked_reports = list(
        Report.objects.filter(reporter=request.user)
        .order_by('-updated_at', '-created_at')[:8]
    )
    linked_reports = linked_reports or None

    profile_reports = []
    if profile is not None:
        related_reports = getattr(profile, "reports", None)
        if related_reports is not None:
            try:
                if hasattr(related_reports, "all"):
                    profile_reports = list(related_reports.all()[:8])
                else:
                    profile_reports = list(related_reports)[:8]
            except Exception:  # pragma: no cover - defensive fallback
                logger.exception("Failed to load reports attached to profile")
                profile_reports = []

    context = {
        "profile": profile,
        "user": request.user,
        "can_edit": True,
        "linked_reports": linked_reports,
        "profile_reports": profile_reports,
        "password_change_url": _safe_reverse('account_change_password'),
        "delete_account_url": _safe_reverse('account_delete'),
        "user_role": getattr(request.user, "role", None),
    }

    return render(request, 'user_portal/profile.html', context)
@csrf_exempt
@require_POST
def set_theme(request):
    """Persist the user's theme preference in the session."""
    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
        theme = data.get('theme')
        if theme in ['light', 'dark']:
            request.session['theme'] = theme
            return JsonResponse({'status': 'ok', 'theme': theme})
        if theme == 'auto':
            request.session.pop('theme', None)
            return JsonResponse({'status': 'ok', 'theme': 'auto'})
    except Exception:
        logger.exception("Failed to set theme")
    return JsonResponse({'status': 'error'}, status=400)