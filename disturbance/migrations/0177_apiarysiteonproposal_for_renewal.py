# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-29 08:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0176_auto_20200929_1158'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='for_renewal',
            field=models.BooleanField(default=False),
        ),
    ]
