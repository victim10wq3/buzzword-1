# Generated by Django 3.0.4 on 2020-04-20 15:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("explore", "0008_corpus_parsed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="corpus",
            name="language",
            field=models.ForeignKey(
                choices=[
                    ("nl", "Dutch"),
                    ("en", "English"),
                    ("fr", "French"),
                    ("de", "German"),
                    ("el", "Greek"),
                    ("it", "Italian"),
                    ("pt", "Portuguese"),
                    ("es", "Spanish"),
                ],
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="explore.Language",
            ),
        ),
    ]
