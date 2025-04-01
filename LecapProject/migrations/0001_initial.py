# Generated by Django 5.1.7 on 2025-04-01 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultRoleRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_id', models.CharField(max_length=50, unique=True, verbose_name='ID роли')),
                ('role_name', models.CharField(max_length=100, verbose_name='Название роли')),
                ('default_rate', models.IntegerField(blank=True, null=True, verbose_name='Стандартная ставка')),
            ],
        ),
        migrations.CreateModel(
            name='ProjectRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_id', models.CharField(max_length=50, verbose_name='ID проекта')),
                ('project_title', models.CharField(max_length=200, verbose_name='Название проекта')),
                ('role_id', models.CharField(max_length=50, verbose_name='ID роли')),
                ('role_name', models.CharField(max_length=100, verbose_name='Название роли')),
                ('rate', models.IntegerField(blank=True, null=True, verbose_name='Почасовая ставка')),
            ],
            options={
                'unique_together': {('project_id', 'role_id')},
            },
        ),
    ]
