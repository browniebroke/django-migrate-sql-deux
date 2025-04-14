from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("author", models.CharField(max_length=200)),
                ("rating", models.IntegerField(null=True, blank=True)),
                ("published", models.BooleanField(default=True)),
            ],
        ),
    ]
