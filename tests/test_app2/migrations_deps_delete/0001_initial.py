from django.db import migrations

import django_migrate_sql.operations


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        django_migrate_sql.operations.CreateSQL(
            name="sale",
            sql="CREATE TYPE sale AS (arg1 int); -- 1",
            reverse_sql="DROP TYPE sale",
        ),
    ]
