
from django.db import migrations

def cleanup_empty_rates(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute("UPDATE LecapProject_projectrate SET rate = NULL WHERE rate = '';")

class Migration(migrations.Migration):

    dependencies = [
        ('LecapProject', '0003_cleanup_rate_field'),
    ]

    operations = [
        migrations.RunPython(cleanup_empty_rates),
    ]
