from django.db import migrations


class Migration(migrations.Migration):
    """Une dos migraciones 0005 independientes: jurados y aspirantes."""

    dependencies = [
        ("participantes", "0005_historial_jurados"),
        ("participantes", "0005_situacion_aspirante"),
    ]

    operations = []
