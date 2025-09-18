import django
from django.conf import settings
from django.db.migrations.autodetector import (
    MigrationAutodetector as DjangoMigrationAutodetector,
)
from django.db.migrations.operations import RunSQL
from django.utils.datastructures import OrderedSet

if django.VERSION >= (5, 1):
    from django.db.migrations.autodetector import OperationDependency

from .graph import SQLStateGraph, build_current_graph
from .operations import AlterSQL, AlterSQLState, CreateSQL, DeleteSQL, ReverseAlterSQL


class SQLBlob:
    pass


# Dummy object used to identify django dependency as the one used by this tool only.
SQL_BLOB = SQLBlob()


def _sql_params(sql):
    """
    Identify `sql` as either SQL string or 2-tuple of SQL and params.
    Same format as supported by Django's RunSQL operation for sql/reverse_sql.
    """
    params = None
    if isinstance(sql, (list, tuple)):
        elements = len(sql)
        if elements == 2:
            sql, params = sql
        else:
            raise ValueError(f"Expected a 2-tuple but got {elements:d}")
    return sql, params


def is_sql_equal(sqls1, sqls2):
    """
    Find out equality of two SQL items.

    See https://docs.djangoproject.com/en/stable/ref/migration-operations/#runsql

    Args:
        sqls1: SQL item, has the same format as supported by Django's RunSQL operation.
        sqls2: SQL item, has the same format as supported by Django's RunSQL operation.

    Returns:
        (bool) `True` if equal, otherwise `False`.

    """
    is_seq1 = isinstance(sqls1, (list, tuple))
    is_seq2 = isinstance(sqls2, (list, tuple))

    if not is_seq1:
        sqls1 = (sqls1,)
    if not is_seq2:
        sqls2 = (sqls2,)

    if len(sqls1) != len(sqls2):
        return False

    for sql1, sql2 in zip(sqls1, sqls2, strict=False):
        sql1, params1 = _sql_params(sql1)
        sql2, params2 = _sql_params(sql2)
        if sql1 != sql2 or params1 != params2:
            return False
    return True


def get_ancestors(node):
    """Logic extracted from Django <2.2 as this is dropped in later versions."""
    if "_ancestors" not in node.__dict__:
        ancestors = []
        for parent in sorted(node.parents, reverse=True):
            ancestors += get_ancestors(parent)
        ancestors.append(node.key)
        node.__dict__["_ancestors"] = list(OrderedSet(ancestors))
    return node.__dict__["_ancestors"]


def get_descendants(node):
    """Logic extracted from Django <2.2 as this is dropped in later versions."""
    if "_descendants" not in node.__dict__:
        descendants = []
        for child in sorted(node.children, reverse=True):
            descendants += get_descendants(child)
        descendants.append(node.key)
        node.__dict__["_descendants"] = list(OrderedSet(descendants))
    return node.__dict__["_descendants"]


class MigrationAutodetector(DjangoMigrationAutodetector):
    """
    Substitutes Django's MigrationAutodetector class, injecting SQL migrations logic.
    """

    def __init__(self, from_state, to_state, questioner=None, to_sql_graph=None):
        super().__init__(from_state, to_state, questioner)
        self.to_sql_graph = to_sql_graph or build_current_graph()
        self.from_sql_graph = getattr(self.from_state, "sql_state", None) or SQLStateGraph()
        self.from_sql_graph.build_graph()
        self._sql_operations = []

    def assemble_changes(self, keys, resolve_keys, sql_state):
        """
        Accepts keys of SQL items available, sorts them and adds additional dependencies.
        Uses graph of `sql_state` nodes to build `keys` and `resolve_keys` into sequence that
        starts with leaves (items that have not dependents) and ends with roots.

        Changes `resolve_keys` argument as dependencies are added to the result.

        Args:
            keys (list): List of migration keys, that are one of create/delete operations, and
                don't require respective reverse operations.
            resolve_keys (list): List of migration keys, that are changing existing items,
                and may require respective reverse operations.
            sql_state (graph.SQLStateGraph): State of SQL items.

        Returns:
            (list) Sorted sequence of migration keys, enriched with dependencies.

        """
        result_keys = []
        all_keys = keys | resolve_keys
        for key in all_keys:
            node = sql_state.node_map[key]
            sql_item = sql_state.nodes[key]
            ancs = get_ancestors(node)[:-1]
            ancs.reverse()
            pos = next((i for i, k in enumerate(result_keys) if k in ancs), len(result_keys))
            result_keys.insert(pos, key)

            if key in resolve_keys and not sql_item.replace:
                # ancestors() and descendants() include key itself, need to cut it out.
                descs = reversed(get_descendants(node)[:-1])
                for desc in descs:
                    if desc not in all_keys and desc not in result_keys:
                        result_keys.insert(pos, desc)
                        # these items added may also need reverse operations.
                        resolve_keys.add(desc)
        return result_keys

    def add_sql_operation(self, app_label, sql_name, operation, dependencies):
        """
        Add SQL operation and register it to be used as dependency for further
        sequential operations.
        """
        if django.VERSION >= (5, 1):
            deps = [
                OperationDependency(
                    app_label=dp[0],
                    model_name=SQL_BLOB,
                    field_name=dp[1],
                    type=self._sql_operations.get(dp),
                )
                for dp in dependencies
            ]
        else:
            deps = [(dp[0], SQL_BLOB, dp[1], self._sql_operations.get(dp)) for dp in dependencies]

        self.add_operation(app_label, operation, dependencies=deps)
        self._sql_operations[(app_label, sql_name)] = operation

    def _generate_reversed_sql(self, keys, changed_keys):
        """
        Generate reversed operations for changes, that require full rollback and creation.
        """
        for key in keys:
            if key not in changed_keys:
                continue
            app_label, sql_name = key
            old_item = self.from_sql_graph.nodes[key]
            new_item = self.to_sql_graph.nodes[key]
            if not old_item.reverse_sql or old_item.reverse_sql == RunSQL.noop or new_item.replace:
                continue

            # migrate backwards
            operation = ReverseAlterSQL(sql_name, old_item.reverse_sql, reverse_sql=old_item.sql)
            sql_deps = [n.key for n in self.from_sql_graph.node_map[key].children]
            sql_deps.append(key)
            self.add_sql_operation(app_label, sql_name, operation, sql_deps)

    def _generate_sql(self, keys, changed_keys):
        """Generate forward operations for changing/creating SQL items."""
        for key in reversed(keys):
            app_label, sql_name = key
            new_item = self.to_sql_graph.nodes[key]
            sql_deps = [n.key for n in self.to_sql_graph.node_map[key].parents]
            reverse_sql = new_item.reverse_sql

            if key in changed_keys:
                operation_cls = AlterSQL
                kwargs = {}
                # in case of replace mode, AlterSQL will hold sql, reverse_sql and
                # state_reverse_sql, the latter one will be used for building state forward
                # instead of reverse_sql.
                if new_item.replace:
                    kwargs["state_reverse_sql"] = reverse_sql
                    reverse_sql = self.from_sql_graph.nodes[key].sql
            else:
                operation_cls = CreateSQL
                kwargs = {"dependencies": list(sql_deps)}

            operation = operation_cls(sql_name, new_item.sql, reverse_sql=reverse_sql, **kwargs)
            sql_deps.append(key)
            self.add_sql_operation(app_label, sql_name, operation, sql_deps)

    def _generate_altered_sql_dependencies(self, dep_changed_keys):
        """
        Generate forward operations for changing/creating SQL item dependencies.

        Dependencies are only in-memory and should be reflecting database dependencies,
        so changing them in SQL config does not alter database. Such actions are
        persisted in separate type operation - `AlterSQLState`.

        Args:
            dep_changed_keys (list): Data about keys, that have their dependencies
                changed. List of tuples (key, removed dependencies, added_dependencies).

        """
        for key, removed_deps, added_deps in dep_changed_keys:
            app_label, sql_name = key
            operation = AlterSQLState(
                sql_name,
                add_dependencies=tuple(added_deps),
                remove_dependencies=tuple(removed_deps),
            )
            sql_deps = [key]
            self.add_sql_operation(app_label, sql_name, operation, sql_deps)

    def _generate_delete_sql(self, delete_keys):
        """
        Generate forward delete operations for SQL items.
        """
        for key in delete_keys:
            app_label, sql_name = key
            old_node = self.from_sql_graph.nodes[key]
            operation = DeleteSQL(sql_name, old_node.reverse_sql, reverse_sql=old_node.sql)
            sql_deps = [n.key for n in self.from_sql_graph.node_map[key].children]
            sql_deps.append(key)
            self.add_sql_operation(app_label, sql_name, operation, sql_deps)

    def generate_sql_changes(self):
        """
        Starting point of this tool, which identifies changes and generates respective
        operations.
        """
        from_keys = set(self.from_sql_graph.nodes.keys())
        to_keys = set(self.to_sql_graph.nodes.keys())
        new_keys = to_keys - from_keys
        delete_keys = from_keys - to_keys
        changed_keys = set()
        dep_changed_keys = []

        for key in from_keys & to_keys:
            old_node = self.from_sql_graph.nodes[key]
            new_node = self.to_sql_graph.nodes[key]

            # identify SQL changes -- these will alter database.
            if not is_sql_equal(old_node.sql, new_node.sql):
                changed_keys.add(key)

            # identify dependencies change
            old_deps = self.from_sql_graph.dependencies[key]
            new_deps = self.to_sql_graph.dependencies[key]
            removed_deps = old_deps - new_deps
            added_deps = new_deps - old_deps
            if removed_deps or added_deps:
                dep_changed_keys.append((key, removed_deps, added_deps))

        # we do basic sort here and inject dependency keys here.
        # operations built using these keys will properly set operation dependencies which will
        # enforce django to build/keep a correct order of operations (stable_topological_sort).
        keys = self.assemble_changes(new_keys, changed_keys, self.to_sql_graph)
        delete_keys = self.assemble_changes(delete_keys, set(), self.from_sql_graph)

        self._sql_operations = {}
        self._generate_reversed_sql(keys, changed_keys)
        self._generate_sql(keys, changed_keys)
        self._generate_delete_sql(delete_keys)
        self._generate_altered_sql_dependencies(dep_changed_keys)

    def check_dependency(self, operation, dependency):
        """
        Enhances default behavior of method by checking dependency for matching operation.
        """
        if django.VERSION >= (5, 1):
            # dependency is a named tuple
            if isinstance(dependency.model_name, SQLBlob):
                # NOTE: we follow the sort order created by `assemble_changes` so we build a fixed chain
                # of operations. thus we should match exact operation here.
                return dependency.type == operation
        else:
            # dependency is a tuple
            if isinstance(dependency[1], SQLBlob):
                # NOTE: we follow the sort order created by `assemble_changes` so we build a fixed chain
                # of operations. thus we should match exact operation here.
                return dependency[3] == operation
        return super().check_dependency(operation, dependency)

    def generate_altered_fields(self):
        """
        Injecting point. This is quite awkward, and i'm looking forward Django for having the logic
        divided into smaller methods/functions for easier enhancement and substitution.
        So far we're doing all the SQL magic in this method.
        """
        result = super().generate_altered_fields()
        self.generate_sql_changes()
        return result

    @staticmethod
    def _resolve_dependency(dependency):
        """
        Return the resolved dependency and a boolean denoting whether or not
        it was swappable.
        """
        if dependency[0] != "__setting__":
            return dependency, False
        resolved_app_label, resolved_object_name = getattr(settings, dependency[1]).split(".")
        if django.VERSION >= (5, 1):
            return (
                OperationDependency(
                    resolved_app_label,
                    resolved_object_name.lower(),
                    dependency[2],
                    dependency[3],
                ),
                True,
            )
        else:
            return (
                (resolved_app_label, resolved_object_name.lower(), *dependency[2:]),
                True,
            )
