from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("participantes", "0006_merge_historial_jurados_situacion_aspirante")]

    operations = [
        migrations.AlterField(
            model_name="evaluacionaspirante", name="antecedentes",
            field=models.DecimalField("puntaje de antecedentes", max_digits=5, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="evaluacionaspirante", name="oposicion",
            field=models.DecimalField("puntaje de oposición", max_digits=5, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="cambioevaluacion", name="antecedentes_despues",
            field=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="cambioevaluacion", name="oposicion_despues",
            field=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True),
        ),
    ]
