# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-10-02 03:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0180_auto_20201001_1134'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apiarysite',
            name='latest_approval_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='disturbance.ApiarySiteOnApproval'),
        ),
        migrations.AlterField(
            model_name='apiarysite',
            name='latest_proposal_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='disturbance.ApiarySiteOnProposal'),
        ),
    ]