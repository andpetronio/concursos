from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("participantes", "0004_evaluacion_aspirante"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="aspirante", name="situacion",
            field=models.CharField(max_length=30, default="inscripto", choices=[
                ("inscripto", "Inscripto"), ("impugnacion_pendiente", "Impugnación en trámite"),
                ("no_habilitado", "No habilitado para oposición"),
                ("excluido", "Excluido por decisión de la autoridad"), ("desistio", "Desistió")]),
        ),
        migrations.CreateModel(
            name="CambioSituacionAspirante",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("tipo", models.CharField(max_length=20, choices=[
                    ("impugnacion", "Registrar impugnación en trámite"),
                    ("no_habilitacion", "No habilitar para la oposición (Jurado, art. 34)"),
                    ("exclusion", "Registrar exclusión por impugnación resuelta"),
                    ("desistimiento", "Registrar desistimiento"),
                    ("rectificacion", "Rectificar o dejar sin efecto la decisión")])),
                ("anterior", models.CharField(max_length=30, choices=[
                    ("inscripto", "Inscripto"), ("impugnacion_pendiente", "Impugnación en trámite"),
                    ("no_habilitado", "No habilitado para oposición"),
                    ("excluido", "Excluido por decisión de la autoridad"), ("desistio", "Desistió")])),
                ("nueva", models.CharField(max_length=30, choices=[
                    ("inscripto", "Inscripto"), ("impugnacion_pendiente", "Impugnación en trámite"),
                    ("no_habilitado", "No habilitado para oposición"),
                    ("excluido", "Excluido por decisión de la autoridad"), ("desistio", "Desistió")])),
                ("fecha_decision", models.DateField(verbose_name="fecha de la actuación")),
                ("clase_documento", models.CharField(max_length=20, choices=[
                    ("acta", "Acta del Jurado"), ("resolucion", "Resolución de la autoridad"),
                    ("nota", "Nota o presentación"), ("otro", "Otra actuación formal")])),
                ("documento", models.CharField(max_length=250, verbose_name="actuación respaldatoria")),
                ("fojas", models.CharField(max_length=50, verbose_name="fojas del expediente")),
                ("fundamento", models.TextField(max_length=1500)),
                ("constancia_comunicacion", models.CharField(max_length=300, blank=True)),
                ("version", models.PositiveIntegerField()),
                ("registrado_en", models.DateTimeField(auto_now_add=True)),
                ("aspirante", models.ForeignKey(to="participantes.aspirante", on_delete=django.db.models.deletion.PROTECT, related_name="historial_situacion")),
                ("usuario", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={"ordering": ["-registrado_en", "-pk"], "default_permissions": (),
                     "constraints": [models.UniqueConstraint(fields=["aspirante", "version"],
                         name="aspirante_situacion_historial_version_unica")]},
        ),
    ]
