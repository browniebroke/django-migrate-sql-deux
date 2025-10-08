import textwrap


class SQLItem:
    """
    Represents any SQL entity (unit), for example function, type, index or trigger.
    """

    def __init__(self, name, sql, reverse_sql=None, dependencies=None, replace=False):
        """
        Args:
            name (str): Name of the SQL item. Should be unique among other items in the current
                application. It is the name that other items can refer to.
            sql (str/tuple): Forward SQL that creates entity.
            reverse_sql (str/tuple, optional): Backward SQL that destroys entity. (DROPs).
            dependencies (list, optional): Collection of item keys, that the current one depends on.
                Each element is a tuple of two: (app, item_name). Order does not matter.
            replace (bool, optional): If `True`, further migrations will not drop previous version
                of item before creating, assuming that a forward SQL replaces. For example Postgres
                `create or replace function` which does not require dropping it previously.
                If `False` then each changed item will get two operations: dropping previous version
                and creating new one.
                Default = `False`.

        """
        self.name = name
        self.sql = self._process_sql(sql)
        self.reverse_sql = self._process_sql(reverse_sql)
        self.dependencies = dependencies or []
        self.replace = replace

    def _process_sql(self, sql):
        """
        Process SQL by applying textwrap.dedent() to strings.

        Args:
            sql (str/tuple/list): SQL string or tuple/list of (sql, params).

        Returns:
            Processed SQL in the same format as input.

        """
        if isinstance(sql, str):
            return textwrap.dedent(sql)
        if isinstance(sql, (tuple, list)):
            return [
                (textwrap.dedent(item[0]), item[1])
                if isinstance(item, (tuple, list))
                else textwrap.dedent(item)
                if isinstance(item, str)
                else item
                for item in sql
            ]
        return sql
