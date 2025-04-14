"""
Replaces built-in Django command and forces it generate SQL item modification operations
into regular Django migrations.
"""

import sys
import warnings

import django
from django.apps import apps
from django.conf import settings
from django.core.management.base import CommandError, no_translations
from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)
from django.db import connections, router
from django.db.migrations import Migration
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import InteractiveMigrationQuestioner, NonInteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.utils import DEFAULT_DB_ALIAS, OperationalError

from ...autodetector import MigrationAutodetector
from ...graph import build_current_graph

if django.VERSION >= (5, 2):

    class DjangoMigrateSQLMixin:
        """Mixin for makemigration command to attach a custom auto-detector."""

        autodetector = MigrationAutodetector
else:

    class DjangoMigrateSQLMixin:
        """Mixin for makemigration command to attach a custom auto-detector."""

        @no_translations
        def handle(self, *app_labels, **options):
            self.written_files = []
            self.verbosity = options.get("verbosity")
            self.interactive = options.get("interactive")
            self.dry_run = options.get("dry_run", False)
            self.merge = options.get("merge", False)
            self.empty = options.get("empty", False)
            self.migration_name = options.get("name", None)
            if self.migration_name and not self.migration_name.isidentifier():
                raise CommandError("The migration name must be a valid Python identifier.")
            self.include_header = options.get("include_header", True)
            check_changes = options.get("check_changes", False)
            if check_changes:
                self.dry_run = True
            self.scriptable = options["scriptable"]
            self.update = options["update"]
            # If logs and prompts are diverted to stderr, remove the ERROR style.
            if self.scriptable:
                self.stderr.style_func = None

            # Make sure the app they asked for exists
            app_labels = set(app_labels)
            bad_app_labels = set()
            for app_label in app_labels:
                try:
                    apps.get_app_config(app_label)
                except LookupError:
                    bad_app_labels.add(app_label)
            if bad_app_labels:
                for app_label in bad_app_labels:
                    self.stderr.write(f"App '{app_label}' could not be found. Is it in INSTALLED_APPS?")
                sys.exit(2)

            # Load the current graph state. Pass in None for the connection so
            # the loader doesn't try to resolve replaced migrations from DB.
            loader = MigrationLoader(None, ignore_no_migrations=True)

            # Raise an error if any migrations are applied before their dependencies.
            consistency_check_labels = {config.label for config in apps.get_app_configs()}
            # Non-default databases are only checked if database routers used.
            aliases_to_check = connections if settings.DATABASE_ROUTERS else [DEFAULT_DB_ALIAS]
            for alias in sorted(aliases_to_check):
                connection = connections[alias]
                if connection.settings_dict["ENGINE"] != "django.db.backends.dummy" and any(
                    # At least one model must be migrated to the database.
                    router.allow_migrate(connection.alias, app_label, model_name=model._meta.object_name)
                    for app_label in consistency_check_labels
                    for model in apps.get_app_config(app_label).get_models()
                ):
                    try:
                        loader.check_consistent_history(connection)
                    except OperationalError as error:
                        warnings.warn(
                            "Got an error checking a consistent migration history "
                            f"performed for database connection '{alias}': {error}",
                            RuntimeWarning,
                            stacklevel=1,
                        )
            # Before anything else, see if there's conflicting apps and drop out
            # hard if there are any and they don't want to merge
            conflicts = loader.detect_conflicts()

            # If app_labels is specified, filter out conflicting migrations for
            # unspecified apps.
            if app_labels:
                conflicts = {
                    app_label: conflict for app_label, conflict in conflicts.items() if app_label in app_labels
                }

            if conflicts and not self.merge:
                name_str = "; ".join(f"{', '.join(names)} in {app}" for app, names in conflicts.items())
                raise CommandError(
                    "Conflicting migrations detected; multiple leaf nodes in the "
                    f"migration graph: ({name_str}).\nTo fix them run "
                    "'python manage.py makemigrations --merge'"
                )

            # If they want to merge and there's nothing to merge, then politely exit
            if self.merge and not conflicts:
                self.log("No conflicts detected to merge.")
                return

            # If they want to merge and there is something to merge, then
            # divert into the merge code
            if self.merge and conflicts:
                return self.handle_merge(loader, conflicts)

            if self.interactive:
                questioner = InteractiveMigrationQuestioner(
                    specified_apps=app_labels,
                    dry_run=self.dry_run,
                    prompt_output=self.log_output,
                )
            else:
                questioner = NonInteractiveMigrationQuestioner(
                    specified_apps=app_labels,
                    dry_run=self.dry_run,
                    verbosity=self.verbosity,
                    log=self.log,
                )

            state = loader.project_state()

            # NOTE: customization. Passing graph to autodetector.
            sql_graph = build_current_graph()

            # Set up autodetector
            autodetector = MigrationAutodetector(
                state,
                ProjectState.from_apps(apps),
                questioner,
                sql_graph,
            )

            # If they want to make an empty migration, make one for each app
            if self.empty:
                if not app_labels:
                    raise CommandError("You must supply at least one app label when using --empty.")
                # Make a fake changes() result we can pass to arrange_for_graph
                changes = {app: [Migration("custom", app)] for app in app_labels}
                changes = autodetector.arrange_for_graph(
                    changes=changes,
                    graph=loader.graph,
                    migration_name=self.migration_name,
                )
                self.write_migration_files(changes)
                return

            # Detect changes
            changes = autodetector.changes(
                graph=loader.graph,
                trim_to_apps=app_labels or None,
                convert_apps=app_labels or None,
                migration_name=self.migration_name,
            )

            if not changes:
                # No changes? Tell them.
                if self.verbosity >= 1:
                    if len(app_labels) == 1:
                        self.log(f"No changes detected in app '{app_labels.pop()}'")
                    elif len(app_labels) > 1:
                        self.log("No changes detected in apps '{}'".format("', '".join(app_labels)))
                    else:
                        self.log("No changes detected")
            else:
                if self.update:
                    self.write_to_last_migration_files(changes)
                else:
                    self.write_migration_files(changes)
                if check_changes:
                    sys.exit(1)


class Command(DjangoMigrateSQLMixin, MakeMigrationsCommand):
    """Custom makemigration command using a custom auto-detector."""
