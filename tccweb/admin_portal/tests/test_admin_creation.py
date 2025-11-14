from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from tccweb.admin_portal.forms import AdminCreationForm, SuperAdminCreationForm
from tccweb.admin_portal.views import SUPER_ADMIN_GROUP_NAME
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


class SuperAdminCreationFormTests(TestCase):
    def test_save_creates_superuser(self):
        form = SuperAdminCreationForm(
            data={
                "username": "new-super-admin",
                "email": "new-super-admin@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "new-super-admin@example.com")


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


class AdminManagementPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.super_admin = User.objects.create_superuser(
            username="shifanabs55",
            email="super@example.com",
            password="SuperPass123",
        )
        self.regular_admin = User.objects.create_superuser(
            username="regular-admin",
            email="regular@example.com",
            password="AdminPass123",
        )
        self.other_admin = User.objects.create_superuser(
            username="other-admin",
            email="other@example.com",
            password="AdminPass123",
        )

        self.super_admin_group, _ = Group.objects.get_or_create(
            name=SUPER_ADMIN_GROUP_NAME
        )
        self.super_admin.groups.add(self.super_admin_group)

    def test_regular_admin_sees_read_only_admin_panel(self):
        self.client.force_login(self.regular_admin)

        response = self.client.get(reverse("admin_user_management"))

        self.assertNotContains(response, "Create Administrator")
        self.assertContains(
            response,
            "Only a super administrator can create or modify administrator accounts.",
        )

    def test_regular_admin_cannot_create_admin(self):
        self.client.force_login(self.regular_admin)

        response = self.client.post(
            reverse("admin_user_management"),
            {
                "form_type": "create_admin",
                "username": "blocked-admin",
                "email": "blocked@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("admin_user_management"))
        self.assertFalse(
            get_user_model().objects.filter(username="blocked-admin").exists()
        )
        self.assertContains(
            response,
            "Only a super administrator can manage administrator accounts.",
        )

    def test_regular_admin_cannot_modify_admin_accounts(self):
        self.client.force_login(self.regular_admin)

        response = self.client.post(
            reverse("admin_user_management"),
            {"user_id": self.other_admin.pk, "action": "disable"},
            follow=True,
        )

        self.assertRedirects(response, reverse("admin_user_management"))
        self.other_admin.refresh_from_db()
        self.assertTrue(self.other_admin.is_active)
        self.assertContains(
            response,
            "Only a super administrator can manage administrator accounts.",
        )

    def test_super_admin_can_create_admin(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("admin_user_management"),
            {
                "form_type": "create_admin",
                "username": "new-admin",
                "email": "new-admin@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("admin_user_management"))
        self.assertTrue(
            get_user_model().objects.filter(username="new-admin").exists()
        )

    def test_super_admin_can_create_super_admin(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("admin_user_management"),
            {
                "form_type": "create_super_admin",
                "username": "second-super-admin",
                "email": "second-super-admin@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("admin_user_management"))
        new_super_admin = get_user_model().objects.get(
            username="second-super-admin"
        )
        self.assertTrue(
            new_super_admin.groups.filter(name=SUPER_ADMIN_GROUP_NAME).exists()
        )

    def test_new_super_admin_inherits_management_privileges(self):
        self.client.force_login(self.super_admin)
        self.client.post(
            reverse("admin_user_management"),
            {
                "form_type": "create_super_admin",
                "username": "delegated-super-admin",
                "email": "delegated@example.com",
                "password1": "SecurePass123",
                "password2": "SecurePass123",
            },
        )

        delegated_super_admin = get_user_model().objects.get(
            username="delegated-super-admin"
        )

        self.client.force_login(delegated_super_admin)
        response = self.client.get(reverse("admin_user_management"))
        self.assertContains(response, "Create Administrator")
        self.assertContains(response, "Create Super Administrator")

        disable_response = self.client.post(
            reverse("admin_user_management"),
            {"user_id": self.other_admin.pk, "action": "disable"},
            follow=True,
        )

        self.assertRedirects(disable_response, reverse("admin_user_management"))
        self.other_admin.refresh_from_db()
        self.assertFalse(self.other_admin.is_active)