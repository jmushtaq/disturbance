# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-10 03:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0149_apiarysitelocation'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysitelocation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='apiarysitelocation',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
