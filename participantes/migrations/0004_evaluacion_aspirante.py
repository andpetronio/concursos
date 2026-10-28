from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("participantes", "0003_jurado_unidad_alter_jurado_cargo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluacionAspirante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("antecedentes", models.DecimalField(verbose_name="puntaje de antecedentes", max_digits=5, decimal_places=2)),
                ("oposicion", models.DecimalField(verbose_name="puntaje de oposición", max_digits=5, decimal_places=2)),
                ("version", models.PositiveIntegerField(default=1, editable=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("aspirante", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                  related_name="evaluacion", to="participantes.aspirante")),
                ("creado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                  related_name="evaluaciones_creadas", to=settings.AUTH_USER_MODEL)),
                ("actualizado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                  related_name="evaluaciones_actualizadas", to=settings.AUTH_USER_MODEL)),
            ], options={"default_permissions": ()},
        ),
        migrations.CreateModel(
            name="CambioEvaluacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("antecedentes_antes", models.DecimalField(max_digits=5, decimal_places=2, null=True)),
                ("oposicion_antes", models.DecimalField(max_digits=5, decimal_places=2, null=True)),
                ("antecedentes_despues", models.DecimalField(max_digits=5, decimal_places=2)),
                ("oposicion_despues", models.DecimalField(max_digits=5, decimal_places=2)),
                ("motivo", models.TextField(max_length=1000, blank=True)),
                ("version", models.PositiveIntegerField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("evaluacion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                  related_name="cambios", to="participantes.evaluacionaspirante")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                  to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-fecha", "-pk"], "default_permissions": ()},
        ),
    ]
