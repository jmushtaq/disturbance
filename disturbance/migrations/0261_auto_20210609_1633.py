# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-09 08:33
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0260_auto_20210609_1620'),
    ]

    operations = [
        migrations.RenameField(
            model_name='apiarysiteonapproval',
            old_name='issuance_on_approval',
            new_name='issuance_details',
        ),
        migrations.AddField(
            model_name='apiarysiteonproposal',
            name='issuance_details',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]