"""Fuente documental para el dictamen con situaciones individuales acreditadas.

No decide sobre las actuaciones ni transforma una situación en una evaluación.
El expediente y la autoridad siguen siendo las fuentes de los hechos jurídicos.
"""
from participantes.models import Aspirante, CambioSituacionAspirante


_RESPALDOS = {
    Aspirante.Situacion.NO_HABILITADO: (
        CambioSituacionAspirante.Tipo.NO_HABILITACION,
        CambioSituacionAspirante.Documento.ACTA,
    ),
    Aspirante.Situacion.EXCLUIDO: (
        CambioSituacionAspirante.Tipo.EXCLUSION,
        CambioSituacionAspirante.Documento.RESOLUCION,
    ),
    Aspirante.Situacion.DESISTIO: (
        CambioSituacionAspirante.Tipo.DESISTIMIENTO,
        None,
    ),
}


def antecedentes_dictamen(concurso):
    """Devuelve (instantánea de incidencias, faltantes) para el proyecto de dictamen.

    La última actuación debe corresponder a la situación vigente. La versión
    del aspirante puede ser mayor por correcciones de datos de inscripción.
    Cualquier impugnación todavía pendiente impide habilitar el borrador.
    """
    aspirantes = list(
        concurso.aspirantes.exclude(situacion=Aspirante.Situacion.INSCRIPTO)
        .select_related('persona').order_by('pk')
    )
    if not aspirantes:
        return [], []
    cambios = CambioSituacionAspirante.objects.filter(
        aspirante_id__in=[a.pk for a in aspirantes]
    ).order_by('aspirante_id', '-version')
    ultimos = {}
    for cambio in cambios:
        ultimos.setdefault(cambio.aspirante_id, cambio)

    incidentes, faltantes = [], []
    for aspirante in aspirantes:
        nombre = f'{aspirante.persona.apellido}, {aspirante.persona.nombre}'
        if aspirante.situacion == Aspirante.Situacion.IMPUGNACION_PENDIENTE:
            faltantes.append(f'Impugnación pendiente de resolución para {nombre}: no se puede emitir el proyecto ordinario.')
            continue
        respaldo = _RESPALDOS.get(aspirante.situacion)
        if respaldo is None:
            faltantes.append(f'Situación de {nombre} sin tratamiento documental para este proyecto.')
            continue
        cambio = ultimos.get(aspirante.pk)
        if (cambio is None or cambio.version > aspirante.version
                or cambio.nueva != aspirante.situacion or cambio.tipo != respaldo[0]
                or (respaldo[1] is not None and cambio.clase_documento != respaldo[1])
                or not all((cambio.fecha_decision, cambio.documento.strip(),
                            cambio.fojas.strip(), cambio.fundamento.strip()))):
            faltantes.append(
                f'Completar y verificar la actuación que respalda la situación de {nombre} '
                '(fecha, documento, fojas y fundamento concordantes).'
            )
            continue
        incidentes.append({
            'aspirante_id': aspirante.pk,
            'situacion': aspirante.situacion,
            'version_aspirante': aspirante.version,
            'actuacion_id': cambio.pk,
            'version_actuacion': cambio.version,
            'tipo': cambio.tipo,
            'clase_documento': cambio.clase_documento,
            'documento': cambio.documento,
            'fojas': cambio.fojas,
            'fundamento': cambio.fundamento,
            'fecha_decision': cambio.fecha_decision.isoformat(),
        })
    return incidentes, faltantes
