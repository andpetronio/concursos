from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0006_cambioetapadocumental_origen")]

    operations = [
        migrations.AddField(
            model_name="controldocumental",
            name="cantidad_cotejada",
            field=models.PositiveIntegerField(null=True, blank=True, editable=False),
        ),
    ]
