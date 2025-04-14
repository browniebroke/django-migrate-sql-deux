from django.db import migrations

import django_migrate_sql.operations


class Migration(migrations.Migration):
    dependencies = [
        ("test_app2", "0001_initial"),
        ("test_app", "0001_initial"),
    ]

    operations = [
        django_migrate_sql.operations.CreateSQL(
            name="book",
            sql="CREATE TYPE book AS (arg1 int); -- 1",
            reverse_sql="DROP TYPE book",
        ),
        django_migrate_sql.operations.CreateSQL(
            name="rating",
            sql="CREATE TYPE rating AS (arg1 int); -- 1",
            reverse_sql="DROP TYPE rating",
        ),
        django_migrate_sql.operations.CreateSQL(
            name="narration",
            sql="CREATE TYPE narration AS (sale1 sale, book1 book, arg1 int); -- 1",
            reverse_sql="DROP TYPE narration",
            dependencies=[("test_app", "book"), ("test_app2", "sale")],
        ),
    ]
