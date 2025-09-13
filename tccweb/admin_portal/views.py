from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.db.models.functions import TruncMonth
from tccweb.core.models import Report, EducationalResource, ReportType, ReportStatus, Quiz
from tccweb.core.forms import EducationalResourceForm, QuizForm, QuizQuestionFormSet
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
import csv
from .forms import CounselorCreationForm

try:
    from tccweb.core.models import Quiz  # or wherever your Quiz model is
except Exception:
    Quiz = None

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
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

    monthly_qs = (
        Report.objects
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    monthly_stats = [{"month": m["month"].strftime("%Y-%m"), "count": m["count"]} for m in monthly_qs]

    type_qs = Report.objects.values("incident_type").annotate(count=Count("id")).order_by("-count")
    type_stats = [{"type": r["incident_type"], "count": r["count"]} for r in type_qs]

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
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
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
    ctx = {
        "reports": reports,
        "types": ReportType.choices,
        "statuses": ReportStatus.choices,
        "locations": locations,
    }
    return render(request, "admin_reports.html", ctx)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
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
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_analytics(request):
    monthly_qs = (
        Report.objects
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    monthly_stats = [{'month': m['month'].strftime('%Y-%m'), 'count': m['count']} for m in monthly_qs]
    type_qs = Report.objects.values('incident_type').annotate(count=Count('id')).order_by('-count')
    type_stats = [{'type': r['incident_type'], 'count': r['count']} for r in type_qs]
    locations = Report.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    return render(
        request,
        'admin_analytics.html',
        {'monthly_stats': monthly_stats, 'type_stats': type_stats, 'reports': locations},
    )

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_awareness(request):
    resources = EducationalResource.objects.all().select_related("created_by").order_by('-created_at')
    try:
        quizzes = Quiz.objects.all().prefetch_related('questions').order_by('-created_at')
    except Exception:
        quizzes = []

    # default forms
    form = EducationalResourceForm()
    quiz_form = QuizForm()
    question_formset = QuizQuestionFormSet(prefix='questions')

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

        elif form_type == 'quiz':
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
def admin_user_management(request):
    counselors = User.objects.filter(is_staff=True, is_superuser=False).order_by('username')
    students = User.objects.filter(is_staff=False).order_by('username')
    form = CounselorCreationForm()
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