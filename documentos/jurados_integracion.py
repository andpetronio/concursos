"""Integración F4M.3: hechos F4L revisados -> instantánea del DOCX.

No presupone vigencias por fecha de dictado; el operador confirma la
composición. Si un acto resolutivo no tiene antecedentes suficientes, el
proyecto posterior no puede omitirlo silenciosamente.
"""
from django.core.exceptions import ValidationError

from participantes.jurados_considerandos import preparar_antecedentes_jurado
from participantes.models import ActuacionJurado


def incorporar_antecedentes_jurado(*, concurso, fecha_corte):
    """Devuelve datos serializables para conservar en GeneracionDocumento."""
    actuaciones = list(ActuacionJurado.objects.filter(concurso=concurso)
                       .select_related("jurado__persona", "antecedente", "resuelto_por")
                       .order_by("pk"))
    resolutivas = [a for a in actuaciones if a.tipo in ("cese", "promocion", "designacion")]
    posteriores = [a for a in resolutivas if a.fecha_actuacion > fecha_corte]
    if posteriores:
        # Los jurados de la ficha son los actuales. Usarlos para un documento
        # anterior al último cambio haría afirmar una composición equivocada.
        raise ValidationError(
            "La fecha indicada precede una modificación del jurado registrada. "
            "Este generador utiliza la composición actual y todavía no reconstruye "
            "jurados históricos para documentos anteriores. Revisá la fecha del proyecto."
        )
    # Una presentación registrada para una fecha posterior al proyecto tampoco
    # forma parte de sus antecedentes, aunque todavía figure pendiente hoy.
    hechos_hasta_fecha = [a for a in actuaciones if a.fecha_actuacion <= fecha_corte]
    vista = preparar_antecedentes_jurado(hechos_hasta_fecha, fecha_documento=fecha_corte)
    faltantes = [f"Resolución {b.resolucion or '(sin número)'}: {falta}"
                 for b in vista.bloques for falta in b.faltantes]
    inconsistencias = [aviso for aviso in vista.advertencias if "sin cese vinculado" in aviso]
    if faltantes or inconsistencias:
        raise ValidationError([
            "No se pueden incorporar los cambios del jurado sin sus antecedentes y fojas.",
            *faltantes, *inconsistencias,
        ])
    return {
        "fecha_corte": fecha_corte.isoformat(),
        "textos": [texto for b in vista.bloques for texto in b.considerandos],
        "resoluciones": [{
            "numero": b.resolucion,
            "fecha": b.fecha_resolucion.isoformat() if b.fecha_resolucion else None,
            "actuaciones": list(b.identificadores_actuacion),
        } for b in vista.bloques],
        # Las presentaciones no resueltas no constituyen ceses.
        "advertencias": list(vista.advertencias),
        "revision_explicita": True,
    }
