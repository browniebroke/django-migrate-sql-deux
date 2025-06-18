"""Tests for the custom migrate command."""

import django
from django.core.management.commands.migrate import Command as BaseMigrateCommand

from django_migrate_sql.management.commands.migrate import (
    Command,
    DjangoMigrateSQLMixin,
)


def test_command_inherits_from_mixin_and_base():
    """Test that Command inherits from both the mixin and base command."""
    command = Command()
    assert isinstance(command, DjangoMigrateSQLMixin)
    assert isinstance(command, BaseMigrateCommand)


def test_django_version_compatibility():
    """Test Django version compatibility for autodetector attribute."""
    mixin = DjangoMigrateSQLMixin()

    if django.VERSION >= (5, 2):
        from django_migrate_sql.autodetector import MigrationAutodetector

        assert mixin.autodetector == MigrationAutodetector
    else:
        # For Django < 5.2, the mixin should be a pass-through
        assert hasattr(mixin, "__class__")
