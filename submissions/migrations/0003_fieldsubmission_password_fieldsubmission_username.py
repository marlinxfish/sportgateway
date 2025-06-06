# Generated by Django 5.2.1 on 2025-05-31 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0002_fieldsubmission_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='fieldsubmission',
            name='password',
            field=models.CharField(blank=True, help_text='Password untuk login ke sistem (disimpan dalam format hash)', max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='fieldsubmission',
            name='username',
            field=models.CharField(blank=True, help_text='Username untuk login ke sistem', max_length=50, null=True, unique=True),
        ),
    ]
