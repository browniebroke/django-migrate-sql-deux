class SQLItem(object):
    """
    Represents any SQL entity (unit), for example function, type, index or trigger.
    """
    def __init__(self, name, sql, reverse_sql=None, dependencies=None, replace=False):
        """
        Args:
            name (str): Name of the SQL item. Should be unique among other items in the current
                application. It is the name that other items can refer to.
            sql (str/tuple): Forward SQL that creates entity.
            drop_sql (str/tuple, optional): Backward SQL that destroyes entity. (DROPs).
            dependencies (list, optional): Collection of item keys, that the current one depends on.
                Each element is a tuple of two: (app, item_name). Order does not matter.
            replace (bool, optional): If `True`, further migrations will not drop previous version
                of item before creating, assuming that a forward SQL replaces. For example Postgre's
                `create or replace function` which does not require dropping it previously.
                If `False` then each changed item will get two operations: dropping previous version
                and creating new one.
                Default = `False`.
        """
        self.name = name
        self.sql = sql
        self.reverse_sql = reverse_sql
        self.dependencies = dependencies or []
        self.replace = replace
