import django
from django.core.management.commands.migrate import (
    Command as MigrateCommand,
)

from django_migrate_sql.autodetector import MigrationAutodetector

if django.VERSION >= (5, 2):

    class DjangoMigrateSQLMixin:
        """Mixin for makemigration command to attach a custom auto-detector."""

        autodetector = MigrationAutodetector

else:

    class DjangoMigrateSQLMixin:
        pass


class Command(DjangoMigrateSQLMixin, MigrateCommand):
    pass
