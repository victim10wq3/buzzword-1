# Generated by Django 3.0.5 on 2020-07-28 10:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compare', '0013_ocrupdate_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='ocrupdate',
            name='accepted',
            field=models.BooleanField(default=False),
        ),
    ]
