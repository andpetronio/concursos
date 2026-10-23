from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("participantes", "0002_aspirante_email_aspirante_expediente_inscripcion_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="jurado",
            name="unidad",
            field=models.CharField(
                "unidad", max_length=200, default="",
                help_text="Indicá la unidad donde presta servicios el integrante; puede ser distinta de la dependencia del concurso.",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="jurado",
            name="cargo",
            field=models.CharField(max_length=150, blank=True),
        ),
    ]
