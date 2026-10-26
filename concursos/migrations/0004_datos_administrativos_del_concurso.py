from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("concursos", "0003_concurso_clasificacion_anterior_and_more")]

    operations = [
        migrations.AddField(model_name="concurso", name="ex_titular",
                            field=models.CharField(blank=True, max_length=200, verbose_name="ex titular del cargo")),
        migrations.AddField(model_name="concurso", name="fecha_baja",
                            field=models.DateField(blank=True, null=True, verbose_name="fecha de baja")),
        migrations.AddField(model_name="concurso", name="motivo_baja",
                            field=models.CharField(blank=True, max_length=500, verbose_name="motivo de baja")),
        migrations.AddField(model_name="concurso", name="resolucion_baja",
                            field=models.CharField(blank=True, max_length=9, verbose_name="resolución de baja (NNNN/NN-R)",
                            validators=[django.core.validators.RegexValidator(
                                "^[0-9]{4}/[0-9]{2}-R$",
                                "Utilizá el formato 3278/26-R (resolución del Rectorado).")])),
        migrations.AddField(model_name="concurso", name="iniciador_tratamiento",
                            field=models.CharField(blank=True, max_length=80, verbose_name="tratamiento del iniciador")),
        migrations.AddField(model_name="concurso", name="iniciador_nombre",
                            field=models.CharField(blank=True, max_length=200, verbose_name="nombre y apellido del iniciador")),
        migrations.AddField(model_name="concurso", name="iniciador_cargo",
                            field=models.CharField(blank=True, max_length=200, verbose_name="cargo del iniciador")),
    ]
