from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("concursos", "0006_jurisdiccion_articulos_vacancia")]
    operations = [
        migrations.AddField(
            model_name="concurso",
            name="resolucion_convocatoria",
            field=models.CharField(
                blank=True, max_length=9,
                verbose_name="resolución oficial de convocatoria",
                help_text="Completá este dato solo cuando la resolución de convocatoria haya sido efectivamente emitida.",
                validators=[django.core.validators.RegexValidator(
                    "^[0-9]{4}/[0-9]{2}-R$",
                    "Utilizá el formato 3278/26-R (resolución emitida por Rectorado).")],
            ),
        ),
    ]
