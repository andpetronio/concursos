from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("concursos", "0007_resolucion_oficial_convocatoria")]

    operations = [
        migrations.AlterField(
            model_name="concurso",
            name="causa_vacancia",
            field=models.CharField(
                blank=True, max_length=20, verbose_name="causa de vacancia",
                choices=[
                    ("", "Seleccioná una causa"), ("nuevo", "Cargo nuevo"),
                    ("traslado", "Cargo trasladado"), ("jubilacion", "Jubilación"),
                    ("renuncia", "Renuncia"), ("fallecimiento", "Fallecimiento"),
                    ("concurso", "Designación por concurso en otro cargo"),
                    ("efectivizacion", "Efectivización en otro cargo"),
                    ("otra", "Otra causa"),
                ],
            ),
        ),
    ]
