"""Management command that provisions default roles and permissions."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


ROLE_PERMISSIONS = {
    "Students": [
        "core.add_report",
        "core.view_own_report",
        "core.view_own_case",
    ],
    "Counselors": [
        "core.view_assigned_report",
        "core.change_report",
        "core.view_assigned_case",
        "counselor_portal.add_casenote",
        "counselor_portal.change_casenote",
    ],
    "Administrators": [
        "core.manage_all_reports",
        "core.change_report",
        "core.delete_report",
        "core.view_assigned_case",
        "core.view_own_case",
        "counselor_portal.view_casenote",
    ],
}


class Command(BaseCommand):
    help = "Create default user groups and assign granular permissions."

    def handle(self, *args, **options):
        with transaction.atomic():
            for group_name, permission_labels in ROLE_PERMISSIONS.items():
                group, created = Group.objects.get_or_create(name=group_name)

                resolved_perms = []
                for perm_label in permission_labels:
                    if "." not in perm_label:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Permission label '{perm_label}' is invalid; expected format 'app_label.codename'."
                            )
                        )
                        continue

                    app_label, codename = perm_label.split(".", 1)
                    try:
                        resolved = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename,
                        )
                        resolved_perms.append(resolved)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Permission {perm_label} is not available yet; run migrations and retry."
                            )
                        )

                group.permissions.set(resolved_perms)
                verb = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{verb} group '{group_name}' with {len(resolved_perms)} permissions."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Role provisioning complete."))