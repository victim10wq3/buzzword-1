# Generated by Django 3.0.6 on 2020-05-25 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("explore", "0012_corpus_pdfs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="corpus",
            name="pdfs",
            field=models.BooleanField(default=False, null=True),
        ),
    ]
