# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-11-16 07:07
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserLoginLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=255)),
                ('login_date', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('login_ip', models.CharField(max_length=128)),
                ('login_success', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-login_date'],
            },
        ),
    ]
