# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-07-08 02:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0101_auto_20200708_1021'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitetransferapiarysite',
            name='customer_selected',
            field=models.BooleanField(default=False),
        ),
    ]
