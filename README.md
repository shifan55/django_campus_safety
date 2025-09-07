
# TCCWeb (Django)

This is a Django port of the original Flask app. It mirrors the main routes and reuses your templates and static assets.

## Quickstart

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Routes mapped
- `/` -> index
- `/login` -> login
- `/logout` -> logout
- `/register` -> register
- `/report-anonymous` -> anonymous report
- `/submit-report` -> authenticated report (requires login)
- `/report-success/<tracking_code>` -> success page
- `/track-report` -> check report status using tracking code
- `/awareness` -> resources/contacts

Static files live under `tccweb/static`. Templates under `tccweb/templates`.

### Notes
- Some Jinja-specific constructs (e.g., `url_for`) need to be converted to Django template tags.
- Flash messages map to Django messages framework.
- The database is SQLite by default; change `DATABASES` in `tccweb/settings.py` if needed.
# django_campus_safety
# django_campus_safety
