from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("concursos", "0005_turno_y_domicilio_trabajo")]
    operations = [
        migrations.AlterField("concurso", "fecha_baja", models.DateField(blank=True, null=True,
            verbose_name="fecha de vacancia")),
        migrations.AddField("concurso", "jurisdiccion", models.CharField(blank=True,
            max_length=20, verbose_name="jurisdicción", choices=[
            ("rectorado", "Rectorado"),
            ("comercio", 'IPU - Escuela de Comercio "Lib. Gral. San Martín"'),
            ("industrial", 'IPU - Escuela Industrial "Domingo F. Sarmiento"'),
            ("central", 'IPU - Colegio Central Universitario "Mariano Moreno"')])),
        migrations.AddField("concurso", "articulo_unidad", models.CharField(blank=True, max_length=5,
            choices=[("", "Sin artículo"), ("el", "el"), ("la", "la"), ("del", "del"), ("de la", "de la")],
            verbose_name="artículo de la unidad")),
        migrations.AddField("concurso", "articulo_dependencia", models.CharField(blank=True, max_length=5,
            choices=[("", "Sin artículo"), ("el", "el"), ("la", "la"), ("del", "del"), ("de la", "de la")],
            verbose_name="artículo de la dependencia inmediata")),
        migrations.AddField("concurso", "articulo_superior", models.CharField(blank=True, max_length=5,
            choices=[("", "Sin artículo"), ("el", "el"), ("la", "la"), ("del", "del"), ("de la", "de la")],
            verbose_name="artículo de la dependencia superior")),
        migrations.AddField("concurso", "articulo_iniciador", models.CharField(blank=True, max_length=5,
            choices=[("", "Sin artículo"), ("el", "el"), ("la", "la"), ("del", "del"), ("de la", "de la")],
            verbose_name="artículo del iniciador")),
        migrations.AddField("concurso", "causa_vacancia", models.CharField(blank=True, max_length=20,
            verbose_name="causa de vacancia", choices=[("", "Seleccioná una causa"), ("nuevo", "Cargo nuevo"),
            ("jubilacion", "Jubilación"), ("renuncia", "Renuncia"), ("fallecimiento", "Fallecimiento"),
            ("concurso", "Designación por concurso en otro cargo"), ("efectivizacion", "Efectivización en otro cargo"),
            ("otra", "Otra causa")])),
        migrations.AddField("concurso", "acto_vacancia", models.CharField(blank=True, max_length=150,
            verbose_name="acto de creación o traslado", help_text="Consigná el acto que conste en el expediente; no se presume resolución de baja.")),
        migrations.AddField("concurso", "detalle_vacancia", models.TextField(blank=True, max_length=1000,
            verbose_name="descripción de otra causa")),
    ]
