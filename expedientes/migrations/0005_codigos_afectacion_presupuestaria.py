from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0004_incorporar_controles_convocatoria")]

    operations = [
        migrations.AddField(model_name="controldocumental", name="partida_principal",
                            field=models.CharField(blank=True, max_length=2, verbose_name="Partida principal (2 dígitos)")),
        migrations.AddField(model_name="controldocumental", name="actividad_presupuestaria",
                            field=models.CharField(blank=True, max_length=2, verbose_name="Actividad (2 dígitos)")),
    ]
