# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-01-13 07:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dtable', '0009_plugins'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dtableplugins',
            name='description',
        ),
        migrations.RemoveField(
            model_name='dtableplugins',
            name='last_modified',
        ),
        migrations.AddField(
            model_name='dtableplugins',
            name='info',
            field=models.TextField(default=''),
        ),
    ]
