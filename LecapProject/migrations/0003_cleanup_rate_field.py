
from django.db import migrations

def cleanup_empty_rates(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("UPDATE LecapProject_projectrate SET rate = NULL WHERE rate = '';")

class Migration(migrations.Migration):

    dependencies = [
        ('LecapProject', '0002_alter_projectrate_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_empty_rates),
    ]
