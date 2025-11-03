from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.core.cache import caches
from django.core.paginator import Paginator
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
from .forms import CounselorCreationForm

logger = logging.getLogger(__name__)

try:
    from tccweb.core.models import Quiz  # or wherever your Quiz model is
except ImportError:
    Quiz = None

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    monthly_qs = [] 
    total_reports = Report.objects.count()
    resolved_reports = Report.objects.filter(status=ReportStatus.RESOLVED).count()
    pending_reports = Report.objects.filter(status=ReportStatus.PENDING).count()
    under_review_reports = Report.objects.filter(status=ReportStatus.UNDER_REVIEW).count()

    resolution_rate = int(round((resolved_reports / total_reports) * 100)) if total_reports else 0

    recent_reports = (
        Report.objects.select_related("assigned_to", "reporter")
        .order_by("-created_at")[:10]
    )

    status_labels = {code: label for code, label in ReportStatus.choices}
    status_codes = list(status_labels.keys())

    monthly_stats = cache.get("dashboard_monthly_stats_v2")
    if monthly_stats is None:
        monthly_qs = (
            Report.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month", "status")
            .annotate(count=Count("id"))
            .order_by("month")
        )

    monthly_data = {}
    for record in monthly_qs:
        month_key = record["month"].strftime("%Y-%m")
        bucket = monthly_data.setdefault(
            month_key,
            {
                "month": month_key,
                "count": 0,
                "statuses": {code: 0 for code in status_codes},
            },
        )
        status = record["status"]
        if status in bucket["statuses"]:
            bucket["statuses"][status] += record["count"]
        else:
            bucket["statuses"][status] = record["count"]
        bucket["count"] += record["count"]

    monthly_stats = list(monthly_data.values())
    cache.set("dashboard_monthly_stats_v2", monthly_stats, 300)

    type_stats = cache.get("dashboard_type_stats_v2") or []
    if not type_stats:
        type_qs = (
            Report.objects
            .values("incident_type", "status")
            .annotate(count=Count("id"))
        )
        type_data = {}
        for record in type_qs:
            type_key = record["incident_type"]
            bucket = type_data.setdefault(
                type_key,
                {
                    "type": type_key,
                    "count": 0,
                    "statuses": {code: 0 for code in status_codes},
                },
            )
            status = record["status"]
            if status in bucket["statuses"]:
                bucket["statuses"][status] += record["count"]
            else:
                bucket["statuses"][status] = record["count"]
            bucket["count"] += record["count"]

        type_stats = sorted(type_data.values(), key=lambda item: item["count"], reverse=True)
        cache.set("dashboard_type_stats_v2", type_stats, 300)

    ctx = {
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "pending_reports": pending_reports,
        "under_review_reports": under_review_reports,
        "resolution_rate": resolution_rate,
        "recent_reports": recent_reports,
        "monthly_stats": monthly_stats,
        "type_stats": type_stats,
        "status_labels": status_labels,
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
        report.assigned_to_id = assigned_to or None
        if status:
            report.status = status
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
    status_labels = {code: label for code, label in ReportStatus.choices}
    status_codes = list(status_labels.keys())

    monthly_stats = cache.get("dashboard_monthly_stats_v2")
    if monthly_stats is None:
        monthly_qs = (
            Report.objects
            .annotate(month=TruncMonth('created_at'))
            .values('month', 'status')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        monthly_data = {}
        for record in monthly_qs:
            month_key = record['month'].strftime('%Y-%m')
            bucket = monthly_data.setdefault(
                month_key,
                {
                    'month': month_key,
                    'count': 0,
                    'statuses': {code: 0 for code in status_codes},
                },
            )
            status = record['status']
            if status in bucket['statuses']:
                bucket['statuses'][status] += record['count']
            else:
                bucket['statuses'][status] = record['count']
            bucket['count'] += record['count']

        monthly_stats = list(monthly_data.values())
        cache.set("dashboard_monthly_stats_v2", monthly_stats, 300)

    type_stats = cache.get("dashboard_type_stats_v2") or []
    if not type_stats:
        type_qs = (
            Report.objects.values('incident_type', 'status')
            .annotate(count=Count('id'))
        )
        type_data = {}
        for record in type_qs:
            type_key = record['incident_type']
            bucket = type_data.setdefault(
                type_key,
                {
                    'type': type_key,
                    'count': 0,
                    'statuses': {code: 0 for code in status_codes},
                },
            )
            status = record['status']
            if status in bucket['statuses']:
                bucket['statuses'][status] += record['count']
            else:
                bucket['statuses'][status] = record['count']
            bucket['count'] += record['count']

        type_stats = sorted(type_data.values(), key=lambda item: item['count'], reverse=True)
        cache.set("dashboard_type_stats_v2", type_stats, 300)

    locations = Report.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    return render(
        request,
        'admin_analytics.html',
        {
            'monthly_stats': monthly_stats,
            'type_stats': type_stats,
            'reports': locations,
            'status_labels': status_labels,
        },
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