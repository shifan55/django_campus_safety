from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import NotSupportedError
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncMonth, TruncWeek
from tccweb.core.models import Report, EducationalResource, ReportStatus, SupportContact
from tccweb.core.forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm, MessageForm
from tccweb.counselor_portal.models import ChatMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


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
    msg_form = MessageForm(request.POST or None)
    if request.method == "POST" and msg_form.is_valid() and report.assigned_to:
        parent_id = msg_form.cleaned_data.get("parent_id")
        parent = ChatMessage.objects.filter(id=parent_id, report=report).first() if parent_id else None
        ChatMessage.create(
            report=report,
            sender=request.user,
            recipient=report.assigned_to,
            message=msg_form.cleaned_data["message"],
            parent=parent,
        )
        return redirect("report_messages", report_id=report.id)
    ChatMessage.objects.filter(report=report, recipient=request.user, is_read=False).update(is_read=True)
    chat_messages = (
        ChatMessage.objects.filter(report=report, parent__isnull=True)
        .select_related("sender")
        .prefetch_related("replies__sender")
    )
    return render(
        request,
        "report_messages.html",
        {"report": report, "chat_messages": chat_messages, "msg_form": msg_form},
    )

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
    return render(request, "user_messages.html", {"threads": threads_qs, "q": q})



def report_success(request, tracking_code):
    return render(request, 'report_success.html', {'tracking_code': tracking_code})


@login_required
@user_passes_test(lambda u: not u.is_staff)
def profile_view(request):
    return render(request, 'profile.html', {'user': request.user})

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
            return JsonResponse({'status': 'ok'})
    except Exception:
        logger.exception("Failed to set theme")
    return JsonResponse({'status': 'error'}, status=400)