
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Report, EducationalResource, SupportContact, ReportType, ReportStatus
from .forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm, EducationalResourceForm
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth
from .models import Report, EducationalResource, SupportContact
from .forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm
from django.contrib.auth.decorators import login_required, user_passes_test

def index(request):
    recent_resources = EducationalResource.objects.filter(is_public=True).order_by('-created_at')[:3]
    return render(request, 'index.html', {'recent_resources': recent_resources})

def awareness(request):
    resources = EducationalResource.objects.filter(is_public=True).order_by('-created_at')
    contacts = SupportContact.objects.filter(is_available=True).order_by('name')
    return render(request, 'awareness.html', {'resources': resources, 'contacts': contacts})

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
                if (user.is_staff or user.is_superuser or
                        getattr(getattr(user, 'role', None), 'value', '') == 'admin'):
                    return redirect('index')  # or some admin dashboard
                if not form.cleaned_data.get("remember_me"):    # Session expires on browser close
                    request.session.set_expiry(0)
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
        if form.is_valid():
            report = Report.objects.create(
                incident_type=form.cleaned_data['incident_type'],
                description=form.cleaned_data['description'],
                incident_date=form.cleaned_data['incident_date'],
                location=form.cleaned_data.get('location',''),
                is_anonymous=True
            )
            return redirect('report_success', report_id=report.id)
    else:
        form = AnonymousReportForm()
    return render(request, 'report_anonymous.html', {'form': form})

@login_required
def dashboard(request):
    # TODO: populate with the user’s reports etc.
    return render(request, 'dashboard.html')

def submit_report(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.is_anonymous = False
            report.save()
            return redirect('report_success', report_id=report.id)
    else:
        form = ReportForm()
    return render(request, 'submit_report.html', {'form': form})

def report_success(request, report_id):
    return render(request, 'report_success.html', {'report_id': report_id})

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_dashboard(request):
    # TODO: add admin metrics/resources
        # Basic counts
    total_reports = Report.objects.count()
    resolved_reports = Report.objects.filter(status=ReportStatus.RESOLVED).count()
    pending_reports = Report.objects.filter(status=ReportStatus.PENDING).count()
    under_review_reports = Report.objects.filter(status=ReportStatus.UNDER_REVIEW).count()

    # % resolution rate
    resolution_rate = int(round((resolved_reports / total_reports) * 100)) if total_reports else 0

    # “recent” table (adjust ordering/limit as you prefer)
    recent_reports = Report.objects.select_related("assigned_to").order_by("-created_at")[:10]

    # Monthly trend data  (last 12 months)
    monthly_qs = (
        Report.objects
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    monthly_stats = [{"month": m["month"].strftime("%Y-%m"), "count": m["count"]} for m in monthly_qs]

    # Type distribution (assuming a CharField/EnumField "incident_type")
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

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_reports(request):
    reports = Report.objects.select_related('reporter', 'assigned_to').all()
    incident_type = request.GET.get('type')
    status = request.GET.get('status')
    start = request.GET.get('start')
    end = request.GET.get('end')
    if incident_type:
        reports = reports.filter(incident_type=incident_type)
    if status:
        reports = reports.filter(status=status)
    if start:
        reports = reports.filter(created_at__date__gte=start)
    if end:
        reports = reports.filter(created_at__date__lte=end)
    ctx = {
        'reports': reports,
        'types': ReportType.choices,
        'statuses': ReportStatus.choices,
    }
    return render(request, 'admin_reports.html', ctx)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_case_assignment(request):
    reports = Report.objects.select_related('assigned_to').all()
    users = User.objects.filter(is_staff=True)
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        assigned_to = request.POST.get('assigned_to')
        status = request.POST.get('status')
        report = get_object_or_404(Report, id=report_id)
        report.assigned_to_id = assigned_to or None
        if status:
            report.status = status
        report.save()
        messages.success(request, 'Report updated.')
        return redirect('admin_case_assignment')
    return render(
        request,
        'admin_case_assignment.html',
        {'reports': reports, 'users': users, 'statuses': ReportStatus.choices},
    )


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


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_awareness(request):
    resources = EducationalResource.objects.all()
    if request.method == 'POST':
        if request.GET.get('delete'):
            resource = get_object_or_404(EducationalResource, id=request.GET['delete'])
            resource.delete()
            messages.success(request, 'Resource deleted.')
            return redirect('admin_awareness')
        form = EducationalResourceForm(request.POST)
        if form.is_valid():
            res = form.save(commit=False)
            res.created_by = request.user
            res.save()
            messages.success(request, 'Resource added.')
            return redirect('admin_awareness')
    else:
        form = EducationalResourceForm()
    return render(request, 'admin_awareness.html', {'form': form, 'resources': resources})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def admin_user_management(request):
    users = User.objects.all().order_by('username')
    if request.method == 'POST':
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
    return render(request, 'admin_user_management.html', {'users': users})

@login_required
def profile_view(request):
    return render(request, "profile.html", {"user": request.user})
