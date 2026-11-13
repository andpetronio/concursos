"""Unificar situaciones vigentes sin reescribir actuaciones históricas."""
from django.db import migrations, models


def unificar_situaciones(apps, schema_editor):
    Aspirante = apps.get_model("participantes", "Aspirante")
    Cambio = apps.get_model("participantes", "CambioSituacionAspirante")
    db = schema_editor.connection.alias

    # Dejar intactos los campos tipo/anterior/nueva del registro de auditoría.
    Cambio.objects.using(db).filter(tipo="no_habilitacion").update(motivo_exclusion="requisitos")
    Cambio.objects.using(db).filter(tipo="exclusion").update(motivo_exclusion="impugnacion_aceptada")
    # Primero el código antiguo 'excluido', después 'no_habilitado': ambos
    # pasarán a compartir la misma situación, pero con distinta causa.
    Aspirante.objects.using(db).filter(situacion="excluido").update(motivo_exclusion="impugnacion_aceptada")
    Aspirante.objects.using(db).filter(situacion="no_habilitado").update(
        situacion="excluido", motivo_exclusion="requisitos"
    )


def revertir_unificacion(apps, schema_editor):
    """Solo puede revertir datos heredados, nunca degradar actuaciones nuevas."""
    Aspirante = apps.get_model("participantes", "Aspirante")
    Cambio = apps.get_model("participantes", "CambioSituacionAspirante")
    db = schema_editor.connection.alias
    originales = Aspirante.objects.using(db).filter(
        situacion="excluido", motivo_exclusion="requisitos"
    )
    for aspirante in originales.iterator():
        ultimo = (Cambio.objects.using(db).filter(aspirante_id=aspirante.pk)
                  .order_by("-version").first())
        if ultimo and (ultimo.tipo != "no_habilitacion" or ultimo.nueva != "no_habilitado"):
            raise RuntimeError(
                "No es seguro revertir una exclusión nueva por requisitos: "
                "se perdería la distinción administrativa."
            )
        Aspirante.objects.using(db).filter(pk=aspirante.pk).update(situacion="no_habilitado")


class Migration(migrations.Migration):
    dependencies = [("participantes", "0007_evaluaciones_parciales")]

    operations = [
        migrations.AddField(
            model_name="aspirante", name="motivo_exclusion",
            field=models.CharField(blank=True, choices=[
                ("requisitos", "Por no cumplir los requisitos"),
                ("impugnacion_aceptada", "Por aceptación de impugnación"),
            ], default="", max_length=30),
        ),
        migrations.AddField(
            model_name="cambiosituacionaspirante", name="motivo_exclusion",
            field=models.CharField(blank=True, choices=[
                ("requisitos", "Por no cumplir los requisitos"),
                ("impugnacion_aceptada", "Por aceptación de impugnación"),
            ], default="", max_length=30),
        ),
        migrations.RunPython(unificar_situaciones, revertir_unificacion),
        migrations.AlterField(
            model_name="aspirante", name="situacion",
            field=models.CharField(choices=[
                ("inscripto", "Inscripto"),
                ("impugnacion_pendiente", "Impugnación en trámite"),
                ("excluido", "Excluido"),
                ("desistio", "Desistió"),
            ], default="inscripto", max_length=30),
        ),
        migrations.AlterField(
            model_name="cambiosituacionaspirante", name="tipo",
            field=models.CharField(choices=[
                ("impugnacion", "Registrar impugnación en trámite"),
                ("no_habilitacion", "No habilitar para la oposición (Jurado, art. 34)"),
                ("exclusion", "Registrar exclusión"),
                ("desistimiento", "Registrar desistimiento"),
                ("rectificacion", "Rectificar o dejar sin efecto la decisión"),
            ], max_length=20),
        ),
        migrations.AlterField(
            model_name="cambiosituacionaspirante", name="anterior",
            field=models.CharField(choices=[
                ("inscripto", "Inscripto"),
                ("impugnacion_pendiente", "Impugnación en trámite"),
                ("excluido", "Excluido"),
                ("desistio", "Desistió"),
                ("no_habilitado", "No habilitado para oposición"),
            ], max_length=30),
        ),
        migrations.AlterField(
            model_name="cambiosituacionaspirante", name="nueva",
            field=models.CharField(choices=[
                ("inscripto", "Inscripto"),
                ("impugnacion_pendiente", "Impugnación en trámite"),
                ("excluido", "Excluido"),
                ("desistio", "Desistió"),
                ("no_habilitado", "No habilitado para oposición"),
            ], max_length=30),
        ),
    ]
