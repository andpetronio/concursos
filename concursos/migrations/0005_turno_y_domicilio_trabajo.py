from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("concursos", "0004_datos_administrativos_del_concurso")]

    operations = [
        migrations.AddField(model_name="concurso", name="turno_trabajo",
            field=models.CharField(blank=True, choices=[("manana", "Mañana (7 a 14 hs)"),
                ("tarde", "Tarde (14 a 21 hs)")], max_length=10, verbose_name="turno de trabajo")),
        migrations.AddField(model_name="concurso", name="domicilio_trabajo",
            field=models.CharField(blank=True, max_length=250, verbose_name="domicilio de trabajo")),
    ]
