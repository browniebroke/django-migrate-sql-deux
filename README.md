# django-migrate-sql-deux

<p align="center">
  <a href="https://github.com/browniebroke/django-migrate-sql-deux/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/browniebroke/django-migrate-sql-deux/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status" >
  </a>
  <a href="https://codecov.io/gh/browniebroke/django-migrate-sql-deux">
    <img src="https://img.shields.io/codecov/c/github/browniebroke/django-migrate-sql-deux.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
</p>
<p align="center">
  <a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat-square" alt="pre-commit">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/django-migrate-sql-deux/">
    <img src="https://img.shields.io/pypi/v/django-migrate-sql-deux.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/django-migrate-sql-deux.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/django-migrate-sql-deux.svg?style=flat-square" alt="License">
</p>

---

**Source Code**: <a href="https://github.com/browniebroke/django-migrate-sql-deux" target="_blank">https://github.com/browniebroke/django-migrate-sql-deux </a>

---

Django Migrations support for raw SQL.

> [!NOTE]
> This package is a fork of the `django-migrate-sql` package, originally published by Bogdan Klichuk. This package appears unmaintained, so we decided to start a fork as we depended on it. Most of the code is from the original author.

## About

This tool implements mechanism for managing changes to custom SQL entities (functions, types, indices, triggers) using built-in migration mechanism. Technically creates a sophistication layer on top of the `RunSQL` Django operation.

## What it does

- Makes maintaining your SQL functions, custom composite types, indices and triggers easier.
- Structures SQL into configuration of **SQL items**, that are identified by names and divided among apps, just like models.
- Automatically gathers and persists changes of your custom SQL into migrations using `makemigrations`.
- Properly executes backwards/forwards keeping integrity of database.
- Create -> Drop -> Recreate approach for changes to items that do not support altering and require dropping and recreating.
- Dependencies system for SQL items, which solves the problem of updating items, that rely on others (for example custom types/functions that use other custom types), and require dropping all dependency tree previously with further recreation.

## What it does not

- Does not parse SQL nor validate queries during `makemigrations` or `migrate` because is database-agnostic. For this same reason setting up proper dependencies is user's responsibility.
- Does not create `ALTER` queries for items that support this, for example `ALTER TYPE` in PostgreSQL, because is database-agnostic. In case your tools allow rolling all the changes through `ALTER` queries, you can consider not using this app **or** restructure migrations manually after creation by nesting generated operations into `` `state_operations `` of [`RunSQL`](https://docs.djangoproject.com/en/1.8/ref/migration-operations/#runsql) that does `ALTER`.
- (**TODO**)During `migrate` does not restore full state of items for analysis, thus does not notify about existing changes to schema that are not migrated **nor** does not recognize circular dependencies during migration execution.

## Installation

Install from PyPi:

```shell
pip install django-migrate-sql-deux
```

Add `django_migrate_sql` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'django_migrate_sql',
]
```

App defines a custom `makemigrations` command, that inherits from Django's core one, so in order `django_migrate_sql` app to kick in, put it **before** any other apps that redefine `makemigrations` command too, following [the official guide](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#overriding-commands) on how to override commands.

### Integrations with other apps

If you want functionality from multiple `makemigrations` commands provided by other apps, you may have to create your own command, inheriting from all the base commands. The core functionality is provided as a mixin `DjangoMigrateSQLMixin` to make this easier. For instance, to integrate with [`django-linear-migrations`](https://github.com/adamchainz/django-linear-migrations), you would write a `makemigrations` command along these lines:

```python
# app1/management/commands/makemigrations.py
from django_linear_migrations.management.commands.makemigrations import Command as LinearMigrationsMakeMigrationsCommand
from django_migrate_sql.management.commands.makemigrations import DjangoMigrateSQLMixin

class Command(DjangoMigrateSQLMixin, LinearMigrationsMakeMigrationsCommand):
    pass
```

Again, you should make sure that the app where your custom command is implemented is placed above all the other apps.

## Usage

### Basic example

1. Create `sql_config.py` module to root of a target app you want to manage custom SQL for.
2. Define SQL items in it (`sql_items`), for example:

   ```python
   # PostgreSQL example.
   # Let's define a simple function and let `django_migrate_sql` manage its changes.

   from django_migrate_sql.config import SQLItem

   sql_items = [
       SQLItem(
           'make_sum',   # name of the item
           'create or replace function make_sum(a int, b int) returns int as $$ '
           'begin return a + b; end; '
           '$$ language plpgsql;',  # forward sql
           reverse_sql='drop function make_sum(int, int);',  # sql for removal
       ),
   ]
   ```

3. Create migration `python manage.py makemigrations`:

   ```
   Migrations for 'app_name':
     0002_auto_xxxx.py:
   - Create SQL "make_sum"
   ```

   You can take a look at content this generated:

   ```python
   from django.db import migrations, models
   import django_migrate_sql.operations


   class Migration(migrations.Migration):
       dependencies = [
           ('app_name', '0001_initial'),
       ]
       operations = [
           django_migrate_sql.operations.CreateSQL(
               name='make_sum',
               sql='create or replace function make_sum(a int, b int) returns int as $$ begin return a + b; end; $$ language plpgsql;',
               reverse_sql='drop function make_sum(int, int);',
           ),
       ]
   ```

4. Execute migration `python manage.py migrate`:

   ```
   Operations to perform:
     Apply all migrations: app_name
   Running migrations:
     Rendering model states... DONE
     Applying app_name.0002_xxxx... OK
   ```

   Check result in `python manage.py dbshell`:

   ```
   db_name=# select make_sum(12, 15);
    make_sum
   ----------
          27
   (1 row)
   ```

### Custom types

Now, say, you want to change the function implementation so that it takes a custom type as argument.

1. Edit your `sql_config.py`:

   ```python
   # PostgreSQL example #2.
   # Function and custom type.

   from django_migrate_sql.config import SQLItem

   sql_items = [
       SQLItem(
           "make_sum",  # name of the item
           "create or replace function make_sum(a mynum, b mynum) returns mynum as $$ "
           "begin return (a.num + b.num, 'result')::mynum; end;"
           "$$ language plpgsql;",  # forward sql
           reverse_sql="drop function make_sum(mynum, mynum);",  # sql for removal
           # depends on `mynum` since takes it as argument. we won't be able to drop function
           # without dropping `mynum` first.
           dependencies=[("app_name", "mynum")],
       ),
       SQLItem(
           "mynum",  # name of the item
           "create type mynum as (num int, name varchar(20));",  # forward sql
           reverse_sql="drop type mynum;",  # sql for removal
       ),
   ]
   ```

2. Generate migration `python manage.py makemigrations`:

   ```
   Migrations for 'app_name':
     0003_xxxx:
       - Reverse alter SQL "make_sum"
       - Create SQL "mynum"
       - Alter SQL "make_sum"
       - Alter SQL state "make_sum"
   ```

   You can take a look at the content this generated:

   ```python
   from django.db import migrations, models
   import django_migrate_sql.operations


   class Migration(migrations.Migration):
       dependencies = [
           ('app_name', '0002_xxxx'),
       ]
       operations = [
           django_migrate_sql.operations.ReverseAlterSQL(
               name='make_sum',
               sql='drop function make_sum(int, int);',
               reverse_sql='create or replace function make_sum(a int, b int) returns int as $$ begin return a + b; end; $$ language plpgsql;',
           ),
           django_migrate_sql.operations.CreateSQL(
               name='mynum',
               sql='create type mynum as (num int, name varchar(20));',
               reverse_sql='drop type mynum;',
           ),
           django_migrate_sql.operations.AlterSQL(
               name='make_sum',
               sql='create or replace function make_sum(a mynum, b mynum) returns mynum as $$ begin return (a.num + b.num, \'result\')::mynum; end; $$ language plpgsql;',
               reverse_sql='drop function make_sum(mynum, mynum);',
           ),
           django_migrate_sql.operations.AlterSQLState(
               name='make_sum',
               add_dependencies=[('app_name', 'mynum')],
           ),
       ]
   ```

   **NOTE:** Previous function is completely dropped before creation because definition of it changed. `CREATE OR REPLACE` would create another version of it, so `DROP` makes it clean.

   **If you put `replace=True` as kwarg to an `SQLItem` definition, it will NOT drop + create it, but just rerun forward SQL, which is `CREATE OR REPLACE` in this example.**

3. Execute migration `python manage.py migrate`:

   ```
   Operations to perform:
     Apply all migrations: app_name
   Running migrations:
     Rendering model states... DONE
     Applying brands.0003_xxxx... OK
   ```

   Check results:

   ```
   db_name=# select make_sum((5, 'a')::mynum, (3, 'b')::mynum);
     make_sum
   ------------
    (8,result)
   (1 row)

   db_name=# select make_sum(12, 15);
   ERROR:  function make_sum(integer, integer) does not exist
   LINE 1: select make_sum(12, 15);
                  ^
   HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
   ```

### Getting further

For more examples see `tests`.

Feel free to [open new issues](https://github.com/browniebroke/django-migrate-sql-deux/issues).
