from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase

from tccweb.admin_portal.forms import AdminCreationForm
from tccweb.user_portal.views import _post_login_destination


class AdminCreationFormTests(TestCase):
    def test_save_creates_superuser_with_admin_flags(self):
        form = AdminCreationForm(
            data={
                "username": "new-admin",
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

        form = AdminCreationForm(
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


class HelpTextFilterTests(TestCase):
    template = Template(
        """{% load form_extras %}{% if field|should_show_deferred_help %}show{% endif %}"""
    )

    def render_should_show(self, form, field_name):
        return self.template.render(Context({"field": form[field_name]})).strip()

    def test_password_help_shown_after_validation_errors(self):
        pristine_form = AdminCreationForm()
        self.assertEqual(self.render_should_show(pristine_form, "password1"), "")

        invalid_form = AdminCreationForm(
            data={
                "username": "admin-one",
                "email": "admin-one@example.com",
                "password1": "password",
                "password2": "password",
            }
        )
        self.assertFalse(invalid_form.is_valid())

        self.assertEqual(self.render_should_show(invalid_form, "password1"), "show")
        self.assertEqual(self.render_should_show(invalid_form, "password2"), "show")

    def test_username_help_shows_only_when_field_invalid(self):
        pristine_form = AdminCreationForm()
        self.assertEqual(self.render_should_show(pristine_form, "username"), "")

        invalid_form = AdminCreationForm(
            data={
                "username": "",
                "email": "admin-two@example.com",
                "password1": "ValidPass123",
                "password2": "ValidPass123",
            }
        )
        self.assertFalse(invalid_form.is_valid())

        self.assertEqual(self.render_should_show(invalid_form, "username"), "show")