import subprocess
from django.core.exceptions import ValidationError

ALLOWED_MIME_TYPES = {"application/pdf", "video/mp4"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

def validate_file_type(value):
    content_type = getattr(value, "content_type", "")
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("Unsupported file type. Only PDF or MP4 allowed.")

def validate_file_size(value):
    if value.size > MAX_UPLOAD_SIZE:
        raise ValidationError("File size must not exceed 10 MB")

def validate_no_malware(value):
    try:
        data = value.read()
        process = subprocess.run(
            ["clamscan", "--no-summary", "-"],
            input=data,
            capture_output=True,
        )
        if process.returncode == 1:
            raise ValidationError("Uploaded file failed malware scan")
        if process.returncode not in (0, 1):
            raise ValidationError("Malware scan could not be completed")
    except FileNotFoundError:
        raise ValidationError("Malware scanner not available")
    finally:
        value.seek(0)