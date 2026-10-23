from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError


# Catálogo histórico de esta ampliación; no importar el catálogo de ejecución.
NUEVOS = ("oficio_apunsj", "notificacion_jurados")


def agregar_controles(apps, schema_editor):
    Concurso = apps.get_model("concursos", "Concurso")
    Control = apps.get_model("expedientes", "ControlDocumental")
    alias = schema_editor.connection.alias
    for concurso_id in Concurso.objects.using(alias).values_list("pk", flat=True).iterator():
        for requisito in NUEVOS:
            Control.objects.using(alias).get_or_create(concurso_id=concurso_id, requisito=requisito)


def revertir_solo_sin_uso(apps, schema_editor):
    Control = apps.get_model("expedientes", "ControlDocumental")
    nuevos = Control.objects.using(schema_editor.connection.alias).filter(requisito__in=NUEVOS)
    if nuevos.exclude(verificado=False, fojas="", observaciones="", responsable__isnull=True,
                       verificado_en__isnull=True, actualizado_por__isnull=True, version=1,
                       historial__isnull=True).exists():
        raise IrreversibleError("No se puede revertir: los controles de Convocatoria tienen datos o historial. Se conservó la información.")
    # Solo semillas intactas, nunca controles utilizados ni los 19 anteriores.
    nuevos.delete()


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0003_controles_convocatoria")]
    operations = [migrations.RunPython(agregar_controles, revertir_solo_sin_uso)]
