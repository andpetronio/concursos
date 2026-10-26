from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0005_codigos_afectacion_presupuestaria")]

    operations = [
        migrations.AddField(
            model_name="cambioetapadocumental", name="origen",
            field=models.CharField(
                choices=[("manual", "Manual"), ("automatico", "Automático")],
                default="manual", max_length=12,
            ),
        ),
    ]
