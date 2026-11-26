import pytest
from django.db.migrations import Migration
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ProjectState

from django_migrate_sql.autodetector import MigrationAutodetector
from django_migrate_sql.operations import CreateSQL

CREATE_VIEW = "CREATE VIEW summary AS SELECT 1 AS n"
DROP_VIEW = "DROP VIEW summary"


@pytest.fixture
def make_sql_app(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))

    def make_app(label, source=None):
        app_name = f"graph_{tmp_path.name}_{label}"
        package = tmp_path / app_name
        package.mkdir()
        (package / "__init__.py").touch()
        if source is not None:
            (package / "sql_config.py").write_text(source)
        return app_name

    return make_app


@pytest.fixture
def migration_history():
    def make_history(app_name):
        previous_state = ProjectState()
        CreateSQL("summary", CREATE_VIEW, reverse_sql=DROP_VIEW).state_forwards(app_name, previous_state)
        graph = MigrationGraph()
        graph.add_node((app_name, "0001_initial"), Migration("0001_initial", app_name))
        return previous_state, graph

    return make_history


@pytest.mark.parametrize("optional_source", [None, "# No SQL items are declared.\n"], ids=["no module", "no export"])
def test_optional_config_does_not_hide_a_healthy_app(make_sql_app, migration_history, settings, optional_source):
    optional_app = make_sql_app("optional", optional_source)
    # Retain support for modules that expose sql_items dynamically.
    healthy_app = make_sql_app(
        "healthy",
        f"""\
from django_migrate_sql.config import SQLItem

def __getattr__(name):
    if name == "sql_items":
        return [SQLItem("summary", {CREATE_VIEW!r}, reverse_sql={DROP_VIEW!r})]
    raise AttributeError(name)
""",
    )
    settings.INSTALLED_APPS = [optional_app, healthy_app]
    previous_state, graph = migration_history(healthy_app)

    detector = MigrationAutodetector(previous_state, ProjectState())
    assert detector.changes(graph) == {}


@pytest.mark.parametrize(
    ("source", "error", "message"),
    [
        ("from django.db import models\nsql_items = [models.Model.missing_view]\n", AttributeError, "missing_view"),
        ("import missing_sql_test_dependency\n", ModuleNotFoundError, "missing_sql_test_dependency"),
        ("from django.db import missing_sql_test_symbol\n", ImportError, "missing_sql_test_symbol"),
    ],
    ids=["attribute error", "missing dependency", "import error"],
)
def test_autodetector_fails_if_sql_config_cannot_initialize(
    make_sql_app, migration_history, settings, source, error, message
):
    broken_app = make_sql_app("broken", source)
    settings.INSTALLED_APPS = [broken_app]
    previous_state, graph = migration_history(broken_app)

    # A broken config must not look like an intentional deletion of the view.
    with pytest.raises(error, match=message):
        MigrationAutodetector(previous_state, ProjectState()).changes(graph)
