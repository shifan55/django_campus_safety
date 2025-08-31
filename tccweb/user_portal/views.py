from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from tccweb.core.models import Report, EducationalResource, SupportContact
from tccweb.core.forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm


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
                if not form.cleaned_data.get("remember_me"):
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
                location=form.cleaned_data.get('location', ''),
                is_anonymous=True
            )
            return redirect('report_success', report_id=report.id)
    else:
        form = AnonymousReportForm()
    return render(request, 'report_anonymous.html', {'form': form})


@login_required
def dashboard(request):
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


@login_required
def profile_view(request):
    return render(request, 'profile.html', {'user': request.user})
