# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2023-07-05 08:12
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0305_auto_20230704_1501'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='gis_info',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='spatialqueryquestion',
            name='operator',
            field=models.CharField(choices=[('Equals', 'Equals'), ('GreaterThan', 'Greather than'), ('LessThan', 'Less than'), ('IsNotNull', 'Is not null')], default='Equals', max_length=40, verbose_name='Operator'),
        ),
    ]