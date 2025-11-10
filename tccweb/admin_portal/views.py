from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.core.cache import caches
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import NoReverseMatch, reverse
from django.templatetags.static import static
import logging

# Use the project's default cache backend for storing dashboard statistics
cache = caches["default"]
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
import csv
from tccweb.core.models import (
    Report,
    EducationalResource,
    ReportType,
    ReportStatus,
)
from tccweb.core.forms import EducationalResourceForm, QuizForm, QuizQuestionFormSet
from tccweb.accounts.forms import ProfileForm
from tccweb.accounts.models import Profile
from .forms import CounselorCreationForm

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
                form.save()
                messages.success(request, 'Counselor account created.')
                return redirect('admin_user_management')
        else:
            uid = request.POST.get('user_id')
            action = request.POST.get('action')
            target = get_object_or_404(User, id=uid)
            if action == 'approve':
                target.is_staff = True
            elif action == 'revoke':
                target.is_staff = False
            target.save()
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
        "impersonate_url": "#",
        "security_logs_url": _safe_reverse("admin_reports"),
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