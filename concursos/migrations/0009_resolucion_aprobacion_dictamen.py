from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("concursos", "0008_causa_vacancia_traslado")]

    operations = [
        migrations.AddField(
            model_name="concurso",
            name="resolucion_aprobacion_dictamen",
            field=models.CharField(
                "resolución oficial de aprobación del dictamen",
                max_length=9, blank=True,
                help_text="Registrar solo cuando la resolución de aprobación del dictamen haya sido emitida.",
                validators=[django.core.validators.RegexValidator(
                    r"^[0-9]{4}/[0-9]{2}-R$",
                    "Utilizá el formato 3278/26-R (resolución del Rectorado).",
                )],
            ),
        ),
    ]
