# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-07-02 08:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0099_remove_annualrentalfee_cost'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ApiaryAnnualRentFee',
            new_name='ApiaryAnnualRentalFee',
        ),
        migrations.RenameModel(
            old_name='ApiaryAnnualRentFeeRunDate',
            new_name='ApiaryAnnualRentalFeeRunDate',
        ),
    ]