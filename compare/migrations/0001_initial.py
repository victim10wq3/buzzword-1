# Generated by Django 3.0.6 on 2020-05-11 14:23

from django.db import migrations, models
import martor.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OCRText",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content", martor.models.MartorField()),
                ("commit_msg", models.CharField(blank=True, max_length=255)),
            ],
        ),
    ]
