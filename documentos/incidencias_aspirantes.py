"""Antecedentes documentados de situaciones individuales para borrador de dictamen.

La situación vigente describe el efecto. El motivo y la actuación identifican
el órgano que decidió y su documento. No se reescribe el historial anterior.
"""
from participantes.models import Aspirante, CambioSituacionAspirante


def _respaldo_concordante(aspirante, cambio):
    if aspirante.situacion == Aspirante.Situacion.DESISTIO:
        return cambio.tipo == CambioSituacionAspirante.Tipo.DESISTIMIENTO and cambio.nueva == aspirante.situacion
    if aspirante.situacion != Aspirante.Situacion.EXCLUIDO:
        return False
    motivo = aspirante.motivo_exclusion
    if motivo == Aspirante.MotivoExclusion.REQUISITOS:
        return (cambio.clase_documento == CambioSituacionAspirante.Documento.ACTA
                and cambio.motivo_exclusion == motivo
                and ((cambio.tipo == CambioSituacionAspirante.Tipo.NO_HABILITACION
                      and cambio.nueva == "no_habilitado")  # asiento histórico intacto
                     or (cambio.tipo == CambioSituacionAspirante.Tipo.EXCLUSION
                         and cambio.nueva == Aspirante.Situacion.EXCLUIDO)))
    if motivo == Aspirante.MotivoExclusion.IMPUGNACION_ACEPTADA:
        return (cambio.tipo == CambioSituacionAspirante.Tipo.EXCLUSION
                and cambio.clase_documento == CambioSituacionAspirante.Documento.RESOLUCION
                and cambio.nueva == Aspirante.Situacion.EXCLUIDO
                and cambio.motivo_exclusion == motivo)
    return False


def antecedentes_dictamen(concurso):
    """(instantánea de incidencias, faltantes). No acepta respaldos incoherentes."""
    aspirantes = list(
        concurso.aspirantes.exclude(situacion=Aspirante.Situacion.INSCRIPTO)
        .select_related("persona").order_by("pk")
    )
    if not aspirantes:
        return [], []
    cambios = CambioSituacionAspirante.objects.filter(
        aspirante_id__in=[a.pk for a in aspirantes]
    ).order_by("aspirante_id", "-version")
    ultimos = {}
    for cambio in cambios:
        ultimos.setdefault(cambio.aspirante_id, cambio)

    incidentes, faltantes = [], []
    for aspirante in aspirantes:
        nombre = f"{aspirante.persona.apellido}, {aspirante.persona.nombre}"
        if aspirante.situacion == Aspirante.Situacion.IMPUGNACION_PENDIENTE:
            faltantes.append(f"Impugnación pendiente de resolución para {nombre}: no se puede emitir el proyecto ordinario.")
            continue
        cambio = ultimos.get(aspirante.pk)
        if (cambio is None or cambio.version > aspirante.version
                or not _respaldo_concordante(aspirante, cambio)
                or not all((cambio.fecha_decision, cambio.documento.strip(),
                            cambio.fojas.strip(), cambio.fundamento.strip()))):
            faltantes.append(
                f"Completar y verificar la actuación que respalda la situación de {nombre} "
                "(motivo, fecha, documento, fojas y fundamento concordantes)."
            )
            continue
        incidentes.append({
            "aspirante_id": aspirante.pk,
            "situacion": aspirante.situacion,
            "motivo_exclusion": aspirante.motivo_exclusion,
            "version_aspirante": aspirante.version,
            "actuacion_id": cambio.pk,
            "version_actuacion": cambio.version,
            "tipo": cambio.tipo,
            "clase_documento": cambio.clase_documento,
            "documento": cambio.documento,
            "fojas": cambio.fojas,
            "fundamento": cambio.fundamento,
            "fecha_decision": cambio.fecha_decision.isoformat(),
        })
    return incidentes, faltantes
