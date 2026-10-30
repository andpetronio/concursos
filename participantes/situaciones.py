"""Actuaciones de aspirantes. Registrar el hecho documentado, no resolverlo en SiCon."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Aspirante, CambioSituacionAspirante
from .services import comprobar_version

DESTINOS = {
    CambioSituacionAspirante.Tipo.IMPUGNACION: Aspirante.Situacion.IMPUGNACION_PENDIENTE,
    CambioSituacionAspirante.Tipo.NO_HABILITACION: Aspirante.Situacion.NO_HABILITADO,
    CambioSituacionAspirante.Tipo.EXCLUSION: Aspirante.Situacion.EXCLUIDO,
    CambioSituacionAspirante.Tipo.DESISTIMIENTO: Aspirante.Situacion.DESISTIO,
    CambioSituacionAspirante.Tipo.RECTIFICACION: Aspirante.Situacion.INSCRIPTO,
}


@transaction.atomic
def registrar_actuacion(*, aspirante, tipo, fecha_decision, clase_documento, documento, fojas,
                      fundamento, usuario, version_esperada, constancia_comunicacion=""):
    if not usuario.has_perms(("concursos.view_concurso", "concursos.change_concurso")):
        raise PermissionDenied
    actual = Aspirante.objects.select_for_update().get(pk=aspirante.pk)
    comprobar_version(actual, version_esperada)
    destino = DESTINOS.get(tipo)
    if destino is None:
        raise ValidationError("Elegí una actuación válida.")
    if not actual.puede_rendir and tipo != CambioSituacionAspirante.Tipo.RECTIFICACION:
        raise ValidationError("Para modificar una situación que impide continuar, registrá primero la rectificación respaldada por una actuación.")
    if destino == actual.situacion:
        raise ValidationError("Esta actuación no cambia la situación vigente. Revisá el historial.")
    if tipo == CambioSituacionAspirante.Tipo.RECTIFICACION and actual.situacion == Aspirante.Situacion.INSCRIPTO:
        raise ValidationError("No hay una situación restrictiva que rectificar.")
    if tipo == CambioSituacionAspirante.Tipo.NO_HABILITACION and clase_documento != "acta":
        raise ValidationError("La no habilitación debe constar en un acta del Jurado.")
    if tipo == CambioSituacionAspirante.Tipo.EXCLUSION and clase_documento != "resolucion":
        raise ValidationError("La exclusión por impugnación aceptada requiere una resolución de la autoridad.")
    if clase_documento not in CambioSituacionAspirante.Documento.values:
        raise ValidationError("Seleccioná el tipo de respaldo documental.")
    from expedientes.validators import normalizar_fojas
    fojas = normalizar_fojas(fojas)
    if not documento.strip() or not fojas or not fundamento.strip():
        raise ValidationError("Indicá documento, fojas y fundamento acreditados en el expediente.")
    # No eliminar evaluaciones históricas: el cuadro de mérito excluye a no habilitados.
    anterior = actual.situacion
    actual.situacion = destino
    actual.version += 1
    actual.actualizado_por = usuario
    actual.full_clean()
    actual.save(update_fields=["situacion", "version", "actualizado_por", "actualizado_en"])
    historial = CambioSituacionAspirante(
        aspirante=actual, tipo=tipo, anterior=anterior, nueva=destino,
        fecha_decision=fecha_decision, clase_documento=clase_documento,
        documento=documento.strip(), fojas=fojas,
        fundamento=fundamento.strip(), constancia_comunicacion=constancia_comunicacion.strip(),
        version=actual.version, usuario=usuario,
    )
    historial.full_clean()
    historial.save()
    return historial
