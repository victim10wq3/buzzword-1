# Generated by Django 3.0.5 on 2020-05-31 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explore', '0014_auto_20200531_0550'),
    ]

    operations = [
        migrations.AlterField(
            model_name='language',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
