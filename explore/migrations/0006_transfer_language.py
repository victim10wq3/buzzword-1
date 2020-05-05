# Generated by Django 3.0 on 2019-12-10 14:10

from django.db import migrations


def transfer_lang(apps, schema_editor):
    Corpus = apps.get_model("explore", "Corpus")
    Language = apps.get_model("explore", "Language")
    for corpus in Corpus.objects.all():
        language, _ = Language.objects.get_or_create(name=corpus.language)
        corpus.language_link = language
        corpus.save()
        language.save()


class Migration(migrations.Migration):

    dependencies = [
        ("explore", "0005_auto_20191210_1410"),
    ]

    operations = [
        migrations.RunPython(transfer_lang),
        migrations.RemoveField(model_name="corpus", name="language"),
        migrations.RenameField(
            model_name="corpus", old_name="language_link", new_name="language",
        ),
    ]
