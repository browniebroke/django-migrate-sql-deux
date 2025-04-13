import django
from django.db.migrations.operations import RunSQL
from django.db.migrations.operations.base import Operation
if django.VERSION >= (5, 1):
    from django.db.migrations.operations.base import OperationCategory

from .graph import SQLStateGraph
from .config import SQLItem


class MigrateSQLMixin(object):
    def get_sql_state(self, state):
        """
        Get SQLStateGraph from state.
        """
        if not hasattr(state, 'sql_state'):
            setattr(state, 'sql_state', SQLStateGraph())
        return state.sql_state


class AlterSQLState(MigrateSQLMixin, Operation):
    """
    Alters in-memory state of SQL item.
    This operation is generated separately from others since it does not affect database.
    """

    if django.VERSION >= (5, 1):
        category = OperationCategory.PYTHON

    def describe(self):
        return 'Alter SQL state "{name}"'.format(name=self.name)

    def deconstruct(self):
        kwargs = {
            'name': self.name,
        }
        if self.add_dependencies:
            kwargs['add_dependencies'] = self.add_dependencies
        if self.remove_dependencies:
            kwargs['remove_dependencies'] = self.remove_dependencies
        return (self.__class__.__name__, [], kwargs)

    def state_forwards(self, app_label, state):
        sql_state = self.get_sql_state(state)
        key = (app_label, self.name)

        if key not in sql_state.nodes:
            # XXX: dummy for `migrate` command, that does not preserve state object.
            # Should fail with error when fixed.
            return

        sql_item = sql_state.nodes[key]

        for dep in self.add_dependencies:
            # we are also adding relations to aggregated SQLItem, but only to restore
            # original items. Still using graph for advanced node/arc manipulations.

            # XXX: dummy `if` for `migrate` command, that does not preserve state object.
            # Fail with error when fixed
            if dep in sql_item.dependencies:
                sql_item.dependencies.remove(dep)
            sql_state.add_lazy_dependency(key, dep)

        for dep in self.remove_dependencies:
            sql_item.dependencies.append(dep)
            sql_state.remove_lazy_dependency(key, dep)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    @property
    def reversible(self):
        return True

    def __init__(self, name, add_dependencies=None, remove_dependencies=None):
        """
        Args:
            name (str): Name of SQL item in current application to alter state for.
            add_dependencies (list):
                Unordered list of dependencies to add to state.
            remove_dependencies (list):
                Unordered list of dependencies to remove from state.
        """
        self.name = name
        self.add_dependencies = add_dependencies or ()
        self.remove_dependencies = remove_dependencies or ()


class BaseAlterSQL(MigrateSQLMixin, RunSQL):
    """
    Base class for operations that alter database.
    """

    if django.VERSION >= (5, 1):
        category = OperationCategory.SQL

    def __init__(self, name, sql, reverse_sql=None, state_operations=None, hints=None):
        super(BaseAlterSQL, self).__init__(sql, reverse_sql=reverse_sql,
                                           state_operations=state_operations, hints=hints)
        self.name = name

    def deconstruct(self):
        name, args, kwargs = super(BaseAlterSQL, self).deconstruct()
        kwargs['name'] = self.name
        return (name, args, kwargs)


class ReverseAlterSQL(BaseAlterSQL):

    if django.VERSION >= (5, 1):
        category = OperationCategory.ALTERATION

    def describe(self):
        return 'Reverse alter SQL "{name}"'.format(name=self.name)


class AlterSQL(BaseAlterSQL):
    """
    Updates SQL item with a new version.
    """

    if django.VERSION >= (5, 1):
        category = OperationCategory.ALTERATION

    def __init__(self, name, sql, reverse_sql=None, state_operations=None, hints=None,
                 state_reverse_sql=None):
        """
        Args:
            name (str): Name of SQL item in current application to alter state for.
            sql (str/list): Forward SQL for item creation.
            reverse_sql (str/list): Backward SQL for reversing create operation.
            state_reverse_sql (str/list): Backward SQL used to alter state of backward SQL
                *instead* of `reverse_sql`. Used for operations generated for items with
                `replace` = `True`.
        """
        super(AlterSQL, self).__init__(name, sql, reverse_sql=reverse_sql,
                                       state_operations=state_operations, hints=hints)
        self.state_reverse_sql = state_reverse_sql

    def deconstruct(self):
        name, args, kwargs = super(AlterSQL, self).deconstruct()
        kwargs['name'] = self.name
        if self.state_reverse_sql:
            kwargs['state_reverse_sql'] = self.state_reverse_sql
        return (name, args, kwargs)

    def describe(self):
        return 'Alter SQL "{name}"'.format(name=self.name)

    def state_forwards(self, app_label, state):
        super(AlterSQL, self).state_forwards(app_label, state)
        sql_state = self.get_sql_state(state)
        key = (app_label, self.name)

        if key not in sql_state.nodes:
            # XXX: dummy for `migrate` command, that does not preserve state object.
            # Fail with error when fixed
            return

        sql_item = sql_state.nodes[key]
        sql_item.sql = self.sql
        sql_item.reverse_sql = self.state_reverse_sql or self.reverse_sql


class CreateSQL(BaseAlterSQL):
    """
    Creates new SQL item in database.
    """

    if django.VERSION >= (5, 1):
        category = OperationCategory.ADDITION

    def describe(self):
        return 'Create SQL "{name}"'.format(name=self.name)

    def deconstruct(self):
        name, args, kwargs = super(CreateSQL, self).deconstruct()
        kwargs['name'] = self.name
        if self.dependencies:
            kwargs['dependencies'] = self.dependencies
        return (name, args, kwargs)

    def __init__(self, name, sql, reverse_sql=None, state_operations=None, hints=None,
                 dependencies=None):
        super(CreateSQL, self).__init__(name, sql, reverse_sql=reverse_sql,
                                        state_operations=state_operations, hints=hints)
        self.dependencies = dependencies or ()

    def state_forwards(self, app_label, state):
        super(CreateSQL, self).state_forwards(app_label, state)
        sql_state = self.get_sql_state(state)

        sql_state.add_node(
            (app_label, self.name),
            SQLItem(self.name, self.sql, self.reverse_sql, list(self.dependencies)),
        )

        for dep in self.dependencies:
            sql_state.add_lazy_dependency((app_label, self.name), dep)


class DeleteSQL(BaseAlterSQL):
    """
    Deltes SQL item from database.
    """

    if django.VERSION >= (5, 1):
        category = OperationCategory.REMOVAL

    def describe(self):
        return 'Delete SQL "{name}"'.format(name=self.name)

    def state_forwards(self, app_label, state):
        super(DeleteSQL, self).state_forwards(app_label, state)
        sql_state = self.get_sql_state(state)

        sql_state.remove_node((app_label, self.name))
        sql_state.remove_lazy_for_child((app_label, self.name))
