# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_migrate_sql.operations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('author', models.CharField(max_length=200)),
                ('rating', models.IntegerField(null=True, blank=True)),
                ('published', models.BooleanField(default=True)),
            ],
        ),
    ]
