from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from tccweb.core.models import Report, EducationalResource, SupportContact
from tccweb.core.forms import LoginForm, RegistrationForm, AnonymousReportForm, ReportForm
from django.conf import settings


def index(request):
    recent_resources = EducationalResource.objects.filter(is_public=True).order_by('-created_at')[:3]
    return render(request, 'index.html', {'recent_resources': recent_resources})


def awareness(request):
    resources = EducationalResource.objects.filter(is_public=True).order_by('-created_at')
    contacts = SupportContact.objects.filter(is_available=True).order_by('name')
    return render(request, 'awareness.html', {'resources': resources, 'contacts': contacts})

def resource_detail(request, resource_id):
    """Return JSON details for a single educational resource."""
    resource = get_object_or_404(EducationalResource, id=resource_id, is_public=True)
    data = {
        "id": resource.id,
        "title": resource.title,
        "content": resource.content,
        "url": resource.url,
        "resource_type": resource.resource_type,
    }
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
    else:
        form = AnonymousReportForm()
        context = {
        'form': form,
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }
    return render(request, 'report_anonymous.html', context)


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


@login_required
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


def report_success(request, tracking_code):
    return render(request, 'report_success.html', {'tracking_code': tracking_code})


@login_required
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
        pass
    return JsonResponse({'status': 'error'}, status=400)