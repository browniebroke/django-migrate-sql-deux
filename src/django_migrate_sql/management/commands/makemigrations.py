"""
Replaces built-in Django command and forces it generate SQL item modification operations
into regular Django migrations.
"""

import sys

import django
from django.apps import apps
from django.core.management.base import CommandError, no_translations
from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)
from django.db.migrations import Migration
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import InteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState

from ...autodetector import MigrationAutodetector
from ...graph import build_current_graph


class Command(MakeMigrationsCommand):
    @no_translations
    def handle(self, *app_labels, **options):
        if django.VERSION >= (4, 1):
            self.written_files = []
        self.verbosity = options.get("verbosity")
        self.interactive = options.get("interactive")
        self.dry_run = options.get("dry_run", False)
        self.merge = options.get("merge", False)
        self.empty = options.get("empty", False)
        self.migration_name = options.get("name", None)
        self.exit_code = options.get("exit_code", False)
        self.include_header = options.get("include_header", True)
        check_changes = options.get("check_changes", False)
        if django.VERSION >= (4, 1):
            self.scriptable = options["scriptable"]
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

        # Before anything else, see if there's conflicting apps and drop out
        # hard if there are any and they don't want to merge
        conflicts = loader.detect_conflicts()

        # If app_labels is specified, filter out conflicting migrations for unspecified apps
        if app_labels:
            conflicts = {app_label: conflict for app_label, conflict in conflicts.items() if app_label in app_labels}

        if conflicts and not self.merge:
            name_str = "; ".join("{} in {}".format(", ".join(names), app) for app, names in conflicts.items())
            raise CommandError(
                f"Conflicting migrations detected ({name_str}).\nTo fix them run "
                "'python manage.py makemigrations --merge'"
            )

        # If they want to merge and there's nothing to merge, then politely exit
        if self.merge and not conflicts:
            self.stdout.write("No conflicts detected to merge.")
            return

        # If they want to merge and there is something to merge, then
        # divert into the merge code
        if self.merge and conflicts:
            return self.handle_merge(loader, conflicts)

        state = loader.project_state()

        # NOTE: customization. Passing graph to autodetector.
        sql_graph = build_current_graph()

        # Set up autodetector
        autodetector = MigrationAutodetector(
            state,
            ProjectState.from_apps(apps),
            InteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=self.dry_run),
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
                    self.stdout.write(f"No changes detected in app '{app_labels.pop()}'")
                elif len(app_labels) > 1:
                    self.stdout.write("No changes detected in apps '{}'".format("', '".join(app_labels)))
                else:
                    self.stdout.write("No changes detected")

            if self.exit_code:
                sys.exit(1)
        else:
            self.write_migration_files(changes)
            if check_changes:
                sys.exit(1)
