
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid

def generate_tracking_code():
    """Generate a short unique tracking code for anonymous lookups."""
    return uuid.uuid4().hex[:10].upper()

class ReportType(models.TextChoices):
    BULLYING = 'bullying', 'Bullying'
    RAGGING = 'ragging', 'Ragging'
    HARASSMENT = 'harassment', 'Harassment'
    OTHER = 'other', 'Other'

class ReportStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    UNDER_REVIEW = 'under_review', 'Under Review'
    RESOLVED = 'resolved', 'Resolved'

class Report(models.Model):
    reporter = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports')
    incident_type = models.CharField(max_length=32, choices=ReportType.choices)
    description = models.TextField()
    incident_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    witness_present = models.BooleanField(default=False)
    previous_incidents = models.BooleanField(default=False)
    support_needed = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    # optional meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reporter_name = models.CharField(max_length=100, blank=True, null=True)
    reporter_email = models.EmailField(blank=True, null=True)
    reporter_phone = models.CharField(max_length=20, blank=True, null=True)
    tracking_code = models.CharField(max_length=12, unique=True, default=generate_tracking_code, editable=False)

    status = models.CharField(max_length=50, choices=ReportStatus.choices, default=ReportStatus.PENDING)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        related_name="assigned_reports",
        on_delete=models.SET_NULL,
    )

    counselor_notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_incident_type_display()} on {self.incident_date:%Y-%m-%d}"
    
    

class EducationalResource(models.Model):
    RESOURCE_TYPES = [
        ("article", "Article"),
        ("video", "Video"),
        ("guide", "Guide"),
        ("quiz", "Quiz"),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to="resources/", blank=True, null=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES, default="article")
    category = models.CharField(max_length=50, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_resources')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Quiz(models.Model):
    """A quiz consisting of multiple questions."""

    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    """Individual question belonging to a Quiz."""

    OPTION_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]

    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200, blank=True)
    option_d = models.CharField(max_length=200, blank=True)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)

    def __str__(self):
        return self.text

class SupportContact(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    office_hours = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

