from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("participantes", "0004_evaluacion_aspirante"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name="jurado", name="vigente",
                            field=models.BooleanField(default=True, editable=False)),
        migrations.RemoveConstraint(model_name="jurado", name="jurado_plaza_unica"),
        migrations.AddConstraint(model_name="jurado", constraint=models.UniqueConstraint(
            fields=["concurso", "representacion", "calidad"],
            condition=models.Q(vigente=True), name="jurado_plaza_vigente_unica")),
        migrations.CreateModel(name="ActuacionJurado", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("tipo", models.CharField(max_length=20, choices=[("presentacion", "Presentación recibida"), ("cese", "Cese por resolución"), ("promocion", "Designación de suplente como titular"), ("designacion", "Nueva designación")])),
            ("motivo", models.CharField(max_length=20, choices=[("excusacion", "Excusación"), ("recusacion", "Recusación")], blank=True)),
            ("representacion", models.CharField(max_length=20, choices=[("dependencia", "Autoridad de dependencia convocante"), ("rectorado", "Rectorado"), ("personal", "Personal de dependencia")])),
            ("calidad_anterior", models.CharField(max_length=10, choices=[("titular", "Titular"), ("suplente", "Suplente")], blank=True)),
            ("calidad_nueva", models.CharField(max_length=10, choices=[("titular", "Titular"), ("suplente", "Suplente")], blank=True)),
            ("fecha_actuacion", models.DateField()),
            ("resolucion", models.CharField(max_length=60, blank=True)),
            ("fojas", models.CharField(max_length=50, blank=True)),
            ("observaciones", models.TextField(max_length=1000, blank=True)),
            ("concurso", models.ForeignKey(to="concursos.concurso", related_name="actuaciones_jurado", on_delete=django.db.models.deletion.PROTECT)),
            ("jurado", models.ForeignKey(to="participantes.jurado", related_name="actuaciones", on_delete=django.db.models.deletion.PROTECT)),
            ("antecedente", models.ForeignKey(to="participantes.actuacionjurado", related_name="movimientos_derivados", null=True, blank=True, on_delete=django.db.models.deletion.PROTECT)),
            ("resuelto_por", models.ForeignKey(to="participantes.actuacionjurado", related_name="presentaciones_resueltas", null=True, blank=True, on_delete=django.db.models.deletion.PROTECT)),
            ("registrado_por", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
            ("registrado_en", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-registrado_en", "-pk"], "default_permissions": ()}),
    ]
