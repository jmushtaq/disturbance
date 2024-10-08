# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-11-06 00:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0271_auto_20211029_1059'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemporaryUsePublicLiabilityInsuranceDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('uploaded_date', models.DateTimeField(auto_now_add=True)),
                ('_file', models.FileField(max_length=255, upload_to='')),
                ('input_name', models.CharField(blank=True, max_length=255, null=True)),
                ('can_delete', models.BooleanField(default=True)),
                ('visible', models.BooleanField(default=True)),
                ('proposal', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='public_liability_insurance_documents', to='disturbance.ProposalApiaryTemporaryUse')),
            ],
        ),
    ]
