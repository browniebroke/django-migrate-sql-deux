import os
import shutil
import tempfile
from contextlib import contextmanager
from importlib import import_module
from io import StringIO

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.test.utils import extend_sys_path
from psycopg2.extras import CompositeCaster, register_composite

from django_migrate_sql.config import SQLItem

from .models import Book


class TupleComposite(CompositeCaster):
    """Loads composite type object as tuple."""

    def make(self, values):
        return tuple(values)


def module_dir(module):
    """
    Find the name of the directory that contains a module, if possible.

    Raise ValueError otherwise, e.g. for namespace packages that are split
    over several directories.
    """
    # Convert to list because _NamespacePath does not support indexing on 3.3.
    paths = list(getattr(module, "__path__", []))
    if len(paths) == 1:
        return paths[0]
    else:
        filename = getattr(module, "__file__", None)
        if filename is not None:
            return os.path.dirname(filename)
    raise ValueError("Cannot determine directory containing %s" % module)


def item(name, version, dependencies=None):
    """
    Creates mock SQL item represented by PG composite type.

    Returns:
        (SQLItem): Resulting composite type:
            * sql = CREATE TYPE <name> AS (
                [<dep1> <dep1_type>, ..., <depN> <depN_type>], arg1 int, arg2 int,
                .., argN int);
            dependencies are arguments, version affects amount of extra int arguments.
            Version = 1 means one int argument.
            * sql = DROP TYPE <name>.

    """
    dependencies = dependencies or ()
    args = ", ".join(
        [f"{dep[1]}{version} {dep[1]}" for dep in dependencies] + [f"arg{i + 1} int" for i in range(version)]
    )
    sql, reverse_sql = (
        f"CREATE TYPE {name} AS ({args}); -- {version}",
        f"DROP TYPE {name}",
    )
    return SQLItem(name, sql, reverse_sql, dependencies=dependencies)


def contains_ordered(lst, order):
    """Checks if `order` sequence exists in `lst` in the defined order."""
    prev_idx = -1
    try:
        for item in order:
            idx = lst.index(item)
            if idx <= prev_idx:
                return False
            prev_idx = idx
    except ValueError:
        return False
    return True


def mig_name(name):
    """Returns name[0] (app name) and first 4 letters of migration name (name[1])."""
    return name[0], name[1][:4]


def run_query(sql, params=None):
    cursor = connection.cursor()
    cursor.execute(sql, params=params)
    return cursor.fetchall()


class BaseMigrateSQLTestCase(TestCase):
    """Tests `migrate_sql` using sample PG functions and their body/argument changes."""

    def setUp(self):
        super().setUp()
        self.config = import_module("tests.test_app.sql_config")
        self.config2 = import_module("tests.test_app2.sql_config")
        self.out = StringIO()

    def tearDown(self):
        super().tearDown()
        if hasattr(self.config, "sql_items"):
            delattr(self.config, "sql_items")
        if hasattr(self.config2, "sql_items"):
            delattr(self.config2, "sql_items")

    def check_migrations_content(self, expected):
        """Check content (operations) of migrations."""
        loader = MigrationLoader(None, load=True)
        available = loader.disk_migrations.keys()
        for expc_mig, (check_exists, dependencies, op_groups) in expected.items():
            key = next((mig for mig in available if mig_name(mig) == mig_name(expc_mig)), None)
            if check_exists:
                self.assertIsNotNone(key, f"Expected migration {expc_mig} not found.")
            else:
                self.assertIsNone(key, f"Unexpected migration {expc_mig} was found.")
                continue
            migration = loader.disk_migrations[key]
            self.assertEqual({mig_name(dep) for dep in migration.dependencies}, set(dependencies))
            mig_ops = [(op.__class__.__name__, op.name) for op in migration.operations]
            for op_group in op_groups:
                self.assertTrue(contains_ordered(mig_ops, op_group))

    @contextmanager
    def temporary_migration_module(self, app_label="test_app", module=None):
        """
        Allows testing management commands in a temporary migrations module.

        The migrations module is used as a template for creating the temporary
        migrations module. If it isn't provided, the application's migrations
        module is used, if it exists.
        Returns the filesystem path to the temporary migrations module.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            target_dir = tempfile.mkdtemp(dir=temp_dir)
            with open(os.path.join(target_dir, "__init__.py"), "w"):
                pass
            target_migrations_dir = os.path.join(target_dir, "migrations")

            if module is None:
                module = apps.get_app_config(app_label).name + ".migrations"

            try:
                source_migrations_dir = module_dir(import_module(module))
            except (ImportError, ValueError):
                pass
            else:
                shutil.copytree(source_migrations_dir, target_migrations_dir)

            with extend_sys_path(temp_dir):
                new_module = os.path.basename(target_dir) + ".migrations"
                new_setting = settings.MIGRATION_MODULES.copy()
                new_setting[app_label] = new_module
                with self.settings(MIGRATION_MODULES=new_setting):
                    yield target_migrations_dir
        finally:
            shutil.rmtree(temp_dir)


class MigrateSQLTestCase(BaseMigrateSQLTestCase):
    SQL_V1 = (
        # sql
        [
            (
                """
            CREATE OR REPLACE FUNCTION top_books()
                RETURNS SETOF test_app_book AS $$
            BEGIN
                RETURN QUERY SELECT * FROM test_app_book ab WHERE ab.rating > %s
                ORDER BY ab.rating DESC;
            END;
            $$ LANGUAGE plpgsql;
          """,
                [5],
            )
        ],
        # reverse sql
        "DROP FUNCTION top_books()",
    )

    SQL_V2 = (
        # sql
        [
            (
                """
            CREATE OR REPLACE FUNCTION top_books(min_rating int = %s)
                RETURNS SETOF test_app_book AS $$
            BEGIN
                RETURN QUERY EXECUTE 'SELECT * FROM test_app_book ab
                    WHERE ab.rating > $1 AND ab.published
                    ORDER BY ab.rating DESC'
                USING min_rating;
            END;
            $$ LANGUAGE plpgsql;
          """,
                [5],
            )
        ],
        # reverse sql
        "DROP FUNCTION top_books(int)",
    )

    SQL_V3 = (
        # sql
        [
            (
                """
            CREATE OR REPLACE FUNCTION top_books()
                RETURNS SETOF test_app_book AS $$
            DECLARE
                min_rating int := %s;
            BEGIN
                RETURN QUERY EXECUTE 'SELECT * FROM test_app_book ab
                    WHERE ab.rating > $1 AND ab.published
                    ORDER BY ab.rating DESC'
                USING min_rating;
            END;
            $$ LANGUAGE plpgsql;
          """,
                [5],
            )
        ],
        # reverse sql
        "DROP FUNCTION top_books()",
    )

    def setUp(self):
        super(MigrateSQLTestCase, self).setUp()
        books = (
            Book(name="Clone Wars", author="John Ben", rating=4, published=True),
            Book(name="The mysterious dog", author="John Ben", rating=6, published=True),
            Book(name="HTML 5", author="John Ben", rating=9, published=True),
            Book(name="Management", author="John Ben", rating=8, published=False),
            Book(name="Python 3", author="John Ben", rating=3, published=False),
        )
        Book.objects.bulk_create(books)

    def check_run_migrations(self, migrations):
        """Launch migrations requested and compare results."""
        for migration, expected in migrations:
            call_command("migrate", "test_app", migration, stdout=self.out)
            if expected:
                result = run_query("SELECT name FROM top_books()")
                self.assertEqual(result, expected)
            else:
                result = run_query("SELECT COUNT(*) FROM pg_proc WHERE proname = 'top_books'")
                self.assertEqual(result, [(0,)])

    def check_migrations(self, content, results, migration_module=None, app_label="test_app"):
        """Checks migrations content and results after being run."""
        with self.temporary_migration_module(module=migration_module):
            call_command("makemigrations", app_label, stdout=self.out)
            self.check_migrations_content(content)

            call_command("migrate", app_label, stdout=self.out)
            self.check_run_migrations(results)

    def test_migration_add(self):
        """Items newly created should be persisted into migrations and created in DB."""
        sql, reverse_sql = self.SQL_V1
        self.config.sql_items = [SQLItem("top_books", sql, reverse_sql)]
        expected_content = {
            ("test_app", "0002"): (
                True,
                [("test_app", "0001")],
                [[("CreateSQL", "top_books")]],
            ),
        }
        expected_results = (("0002", [("HTML 5",), ("Management",), ("The mysterious dog",)]),)
        self.check_migrations(expected_content, expected_results)

    def test_migration_change(self):
        """Items changed should persist changes into migrations and alter DB."""
        sql, reverse_sql = self.SQL_V2
        self.config.sql_items = [SQLItem("top_books", sql, reverse_sql)]

        expected_content = {
            ("test_app", "0003"): (
                True,
                [("test_app", "0002")],
                [[("ReverseAlterSQL", "top_books"), ("AlterSQL", "top_books")]],
            ),
        }
        expected_results = (
            ("0003", [("HTML 5",), ("The mysterious dog",)]),
            ("0002", [("HTML 5",), ("Management",), ("The mysterious dog",)]),
            ("0001", None),
        )
        self.check_migrations(expected_content, expected_results, "tests.test_app.migrations_change")

    def test_migration_replace(self):
        """
        Items changed with `replace` = True should properly persist changes into
        migrations and replace object in database without reversing previously.
        """
        sql, reverse_sql = self.SQL_V3
        self.config.sql_items = [SQLItem("top_books", sql, reverse_sql, replace=True)]

        expected_content = {
            ("test_app", "0003"): (
                True,
                [("test_app", "0002")],
                [[("AlterSQL", "top_books")]],
            ),
        }
        expected_results = (
            ("0003", [("HTML 5",), ("The mysterious dog",)]),
            ("0002", [("HTML 5",), ("Management",), ("The mysterious dog",)]),
            ("0001", None),
            ("0002", [("HTML 5",), ("Management",), ("The mysterious dog",)]),
        )
        self.check_migrations(expected_content, expected_results, "tests.test_app.migrations_change")

    def test_migration_delete(self):
        """
        Items deleted should embed deletion into migration and run backward SQL in DB.
        """
        self.config.sql_items = []

        expected_content = {
            ("test_app", "0003"): (
                True,
                [("test_app", "0002")],
                [[("DeleteSQL", "top_books")]],
            ),
        }
        expected_results = (("0003", None),)
        self.check_migrations(expected_content, expected_results, "tests.test_app.migrations_change")

    def test_migration_recreate(self):
        """
        Items created after deletion should properly embed recreation into
        migration and alter DB.
        """
        sql, reverse_sql = self.SQL_V2
        self.config.sql_items = [SQLItem("top_books", sql, reverse_sql)]

        expected_content = {
            ("test_app", "0004"): (
                True,
                [("test_app", "0003")],
                [[("CreateSQL", "top_books")]],
            ),
        }
        expected_results = (
            ("0003", None),
            ("0002", [("HTML 5",), ("Management",), ("The mysterious dog",)]),
        )
        self.check_migrations(expected_content, expected_results, "tests.test_app.migrations_recreate")


class SQLDependenciesTestCase(BaseMigrateSQLTestCase):
    """
    Tests SQL item dependencies system.
    """

    # Expected datasets (input and output) for different migration states.
    # When migration is run, database is checked against expected result.
    # Key = name of migration (app, name), value is a list of :
    # * SQL arguments passed to Postgre's ROW
    # * composite type to cast ROW built above into.
    # * dependency types (included into psycopg2 `register_composite`)
    # * expected result after fetching built ROW from database.
    RESULTS_EXPECTED = {  # noqa: RUF012
        ("test_app", "0004"): [
            # product check
            (
                "(('(1, 2)', '(3)', 4, 5), (('(6, 7)', '(8)', 9, 10), 11), '(12)', 13)",
                "product",
                ["product", "book", "author", "rating", "sale", "edition"],
                (((1, 2), (3,), 4, 5), (((6, 7), (8,), 9, 10), 11), (12,), 13),
            ),
            # narration check
            (
                "('(1, 2)', ('(3, 4)', '(5)', 6, 7), 8)",
                "narration",
                ["narration", "book", "sale", "rating"],
                ((1, 2), ((3, 4), (5,), 6, 7), 8),
            ),
        ],
        ("test_app", "0002"): [
            # narration check
            (
                "('(1)', '(2)', 3)",
                "narration",
                ["rating", "book", "sale", "narration"],
                ((1,), (2,), 3),
            ),
        ],
        ("test_app2", "zero"): [
            # edition check
            (None, "edition", [], None),
            # ratings check
            (None, "ratings", [], None),
        ],
        ("test_app", "0005"): [
            # narration check
            ("(1)", "edition", ["edition"], (1,)),
            # product check
            (None, "product", [], None),
        ],
        ("test_app2", "0003"): [
            # sale check
            (None, "sale", [], None),
        ],
    }

    def check_type(self, repr_sql, fetch_type, known_types, expect):
        """
        Checks composite type structure and format.
        """
        cursor = connection.cursor()
        if repr_sql:
            for _type in known_types:
                register_composite(str(_type), cursor.cursor, factory=TupleComposite)

            sql = f"SELECT ROW{repr_sql}::{fetch_type}"
            cursor.execute(sql)
            result = cursor.fetchone()[0]
            self.assertEqual(result, expect)
        else:
            result = run_query("SELECT COUNT(*) FROM pg_type WHERE typname = %s", [fetch_type])
            self.assertEqual(result, [(0,)])

    def check_migrations(self, content, migrations, module=None, module2=None):
        """
        Checks migrations content and result after being run.
        """
        with self.temporary_migration_module(app_label="test_app", module=module):
            with self.temporary_migration_module(app_label="test_app2", module=module2):
                call_command("makemigrations", stdout=self.out)
                self.check_migrations_content(content)

                for app_label, migration in migrations:
                    call_command("migrate", app_label, migration, stdout=self.out)
                    check_cases = self.RESULTS_EXPECTED[(app_label, migration)]
                    for check_case in check_cases:
                        self.check_type(*check_case)

    def test_deps_create(self):
        """
        Creating a graph of items with dependencies should embed
        relations in migrations.
        """
        self.config.sql_items = [
            item("rating", 1),
            item("book", 1),
            item("narration", 1, [("test_app2", "sale"), ("test_app", "book")]),
        ]
        self.config2.sql_items = [item("sale", 1)]
        expected_content = {
            ("test_app2", "0001"): (
                True,
                [],
                [[("CreateSQL", "sale")]],
            ),
            ("test_app", "0002"): (
                True,
                [("test_app2", "0001"), ("test_app", "0001")],
                [
                    [("CreateSQL", "rating")],
                    [("CreateSQL", "book"), ("CreateSQL", "narration")],
                ],
            ),
        }
        migrations = (("test_app", "0002"),)
        self.check_migrations(expected_content, migrations)

    def test_deps_update(self):
        """
        Updating a graph of items with dependencies should embed
        relation changes in migrations.
        """
        self.config.sql_items = [
            item("rating", 1),
            item("edition", 1),
            item("author", 1, [("test_app", "book")]),
            item("narration", 1, [("test_app2", "sale"), ("test_app", "book")]),
            item("book", 2, [("test_app2", "sale"), ("test_app", "rating")]),
            item(
                "product",
                1,
                [("test_app", "book"), ("test_app", "author"), ("test_app", "edition")],
            ),
        ]
        self.config2.sql_items = [item("sale", 2)]

        expected_content = {
            ("test_app", "0003"): (
                True,
                [("test_app", "0002")],
                [
                    [("CreateSQL", "edition")],
                    [("ReverseAlterSQL", "narration"), ("ReverseAlterSQL", "book")],
                ],
            ),
            ("test_app2", "0002"): (
                True,
                [("test_app", "0003"), ("test_app2", "0001")],
                [[("ReverseAlterSQL", "sale"), ("AlterSQL", "sale")]],
            ),
            ("test_app", "0004"): (
                True,
                [("test_app2", "0002"), ("test_app", "0003")],
                [
                    [
                        ("AlterSQL", "book"),
                        ("CreateSQL", "author"),
                        ("CreateSQL", "product"),
                    ],
                    [("AlterSQL", "book"), ("AlterSQL", "narration")],
                    [("AlterSQL", "book"), ("AlterSQLState", "book")],
                ],
            ),
        }
        migrations = (
            ("test_app", "0004"),
            ("test_app", "0002"),
            ("test_app", "0004"),
        )
        self.check_migrations(
            expected_content,
            migrations,
            module="tests.test_app.migrations_deps_update",
            module2="tests.test_app2.migrations_deps_update",
        )

    def test_deps_circular(self):
        """
        Graph with items that refer to themselves in their dependencies
        should raise an error.
        """
        from django.db.migrations.graph import CircularDependencyError

        self.config.sql_items = [
            item("narration", 1, [("test_app2", "sale"), ("test_app", "book")]),
            item("book", 2, [("test_app2", "sale"), ("test_app", "narration")]),
        ]
        self.config2.sql_items = [item("sale", 1)]

        with self.assertRaises(CircularDependencyError):
            self.check_migrations(
                {},
                (),
                module="tests.test_app.migrations_deps_update",
                module2="tests.test_app2.migrations_deps_update",
            )

    def test_deps_no_changes(self):
        """
        In case no changes are made to structure of sql config, no migrations
        should be created.
        """
        self.config.sql_items = [
            item("rating", 1),
            item("book", 1),
            item("narration", 1, [("test_app2", "sale"), ("test_app", "book")]),
        ]
        self.config2.sql_items = [item("sale", 1)]

        expected_content = {
            ("test_app", "0003"): (False, [], []),
            ("test_app2", "0002"): (False, [], []),
        }
        migrations = ()
        self.check_migrations(
            expected_content,
            migrations,
            module="tests.test_app.migrations_deps_update",
            module2="tests.test_app2.migrations_deps_update",
        )

    def test_deps_delete(self):
        """
        Graph with items that gets some of them removed along with dependencies
        should reflect changes into migrations.
        """
        self.config.sql_items = [
            item("rating", 1),
            item("edition", 1),
        ]
        self.config2.sql_items = []

        expected_content = {
            ("test_app", "0005"): (
                True,
                [("test_app", "0004")],
                [
                    [("DeleteSQL", "narration"), ("DeleteSQL", "book")],
                    [
                        ("DeleteSQL", "product"),
                        ("DeleteSQL", "author"),
                        ("DeleteSQL", "book"),
                    ],
                ],
            ),
            ("test_app2", "0003"): (
                True,
                [("test_app", "0005"), ("test_app2", "0002")],
                [[("DeleteSQL", "sale")]],
            ),
        }
        migrations = (
            ("test_app", "0005"),
            ("test_app", "0002"),
            ("test_app2", "zero"),
            ("test_app", "0005"),
            ("test_app2", "0003"),
            ("test_app", "0004"),
        )
        self.check_migrations(
            expected_content,
            migrations,
            module="tests.test_app.migrations_deps_delete",
            module2="tests.test_app2.migrations_deps_delete",
        )
