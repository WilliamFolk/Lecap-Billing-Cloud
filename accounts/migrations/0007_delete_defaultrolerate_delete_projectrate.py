# Generated by Django 5.1.7 on 2025-04-01 16:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_defaultrolerate_projectrate'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DefaultRoleRate',
        ),
        migrations.DeleteModel(
            name='ProjectRate',
        ),
    ]
