# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_migrate_sql.operations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        django_migrate_sql.operations.CreateSQL(
            name='sale',
            sql='CREATE TYPE sale AS (arg1 int); -- 1',
            reverse_sql='DROP TYPE sale',
        ),
    ]
