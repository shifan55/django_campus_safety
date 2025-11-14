from django.contrib.auth import get_user_model
from django.test import TestCase

from tccweb.admin_portal.forms import SubAdminCreationForm
from tccweb.user_portal.views import _post_login_destination


class SubAdminCreationFormTests(TestCase):
    def test_save_creates_superuser_with_admin_flags(self):
        form = SubAdminCreationForm(
            data={
                "username": "new-sub-admin",
                "email": "new-admin@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "new-admin@example.com")

    def test_email_must_be_unique_case_insensitive(self):
        User = get_user_model()
        User.objects.create_user(
            username="existing-admin",
            email="existing@example.com",
            password="SecurePass123",
        )

        form = SubAdminCreationForm(
            data={
                "username": "another-admin",
                "email": "Existing@Example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class PostLoginDestinationTests(TestCase):
    def test_superusers_redirect_to_admin_dashboard(self):
        User = get_user_model()
        user = User.objects.create_superuser(
            username="redirect-admin",
            email="redirect@example.com",
            password="SecurePass123",
        )

        self.assertEqual(_post_login_destination(user), "admin_dashboard")