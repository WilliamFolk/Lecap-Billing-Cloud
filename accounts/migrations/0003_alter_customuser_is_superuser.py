# Generated by Django 5.1.7 on 2025-03-24 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_adminsettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='is_superuser',
            field=models.BooleanField(default=False, help_text='(Designates that this user has all permissions without explicitly assigning them.)', verbose_name='superuser status'),
        ),
    ]
