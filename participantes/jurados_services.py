"""F4L: operaciones formales de integración, registradas sin borrado histórico."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from concursos.models import Concurso
from .models import ActuacionJurado, Jurado
from .services import comprobar_version, crear_participacion


def plaza_con_antecedentes(*, concurso, representacion, calidad):
    """Incluye a los suplentes que fueron promovidos (ya no ocupan la plaza suplente)."""
    return (
        Jurado.todos.filter(concurso=concurso, representacion=representacion, calidad=calidad).exists()
        or ActuacionJurado.objects.filter(
            concurso=concurso, representacion=representacion, calidad_anterior=calidad,
        ).exists()
    )


def _autorizado(usuario):
    if not usuario.has_perms(("concursos.view_concurso", "concursos.change_concurso")):
        raise PermissionDenied


@transaction.atomic
def registrar_presentacion(*, jurado_id, concurso_id, usuario, version_esperada,
                          motivo, fecha_actuacion, fojas="", observaciones=""):
    _autorizado(usuario)
    Concurso.objects.select_for_update().get(pk=concurso_id)
    jurado = Jurado.todos.select_for_update().get(pk=jurado_id, concurso_id=concurso_id)
    comprobar_version(jurado, version_esperada)
    if not jurado.vigente:
        raise ValidationError("El integrante ya no está vigente.")
    if ActuacionJurado.objects.filter(jurado=jurado, tipo="presentacion", resuelto_por__isnull=True).exists():
        raise ValidationError("Ya existe una presentación pendiente para este integrante. Resolvela antes de registrar otra.")
    return ActuacionJurado.objects.create(
        concurso_id=concurso_id, jurado=jurado, tipo="presentacion", motivo=motivo,
        representacion=jurado.representacion, calidad_anterior=jurado.calidad,
        fecha_actuacion=fecha_actuacion, fojas=fojas, observaciones=observaciones,
        registrado_por=usuario,
    )


@transaction.atomic
def resolver_presentacion(*, jurado_id, concurso_id, presentacion_id, usuario,
                            version_esperada, resolucion, fecha_resolucion, fojas="",
                            observaciones="", promover_suplente=False):
    """Primero cesa el titular, luego asciende su suplente, en una misma transacción."""
    _autorizado(usuario)
    Concurso.objects.select_for_update().get(pk=concurso_id)
    jurado = Jurado.todos.select_for_update().get(pk=jurado_id, concurso_id=concurso_id)
    comprobar_version(jurado, version_esperada)
    if not jurado.vigente:
        raise ValidationError("El integrante ya dejó de estar vigente.")
    try:
        presentacion = ActuacionJurado.objects.select_for_update().get(
            pk=presentacion_id, jurado=jurado, concurso_id=concurso_id,
            tipo="presentacion", resuelto_por__isnull=True,
        )
    except ActuacionJurado.DoesNotExist as error:
        raise ValidationError("La presentación ya fue resuelta o no corresponde a este jurado.") from error
    suplente = None
    if jurado.calidad == Jurado.Calidad.TITULAR:
        suplente = Jurado.todos.select_for_update().filter(
            concurso_id=concurso_id, representacion=jurado.representacion,
            calidad=Jurado.Calidad.SUPLENTE, vigente=True,
        ).first()
        if suplente and ActuacionJurado.objects.filter(
            jurado=suplente, tipo="presentacion", resuelto_por__isnull=True,
        ).exists():
            raise ValidationError(
                "El suplente también tiene una presentación pendiente. Si la resolución acepta ambos ceses, "
                "registrá primero la baja formal del suplente; después la del titular."
            )
        if bool(suplente) != bool(promover_suplente):
            raise ValidationError(
                "Si hay suplente vigente en esta representación, la resolución debe disponer su designación "
                "como titular; si no existe, la plaza queda vacante."
            )
    elif promover_suplente:
        raise ValidationError("Solo puede designarse titular al suplente cuando cesa el titular vigente.")
    if fecha_resolucion < presentacion.fecha_actuacion:
        raise ValidationError("La fecha de resolución no puede ser anterior a la presentación.")
    if not resolucion.strip():
        raise ValidationError("La resolución rectoral es obligatoria para registrar el cese.")
    calidad_previa = jurado.calidad
    jurado.vigente = False
    jurado.actualizado_por = usuario
    jurado.version += 1
    jurado.save(update_fields=["vigente", "actualizado_por", "version", "actualizado_en"])
    baja = ActuacionJurado.objects.create(
        concurso_id=concurso_id, jurado=jurado, tipo="cese", motivo=presentacion.motivo,
        representacion=jurado.representacion, calidad_anterior=calidad_previa,
        fecha_actuacion=fecha_resolucion, resolucion=resolucion, fojas=fojas,
        observaciones=observaciones, antecedente=presentacion, registrado_por=usuario,
    )
    presentacion.resuelto_por = baja
    presentacion.save(update_fields=["resuelto_por"])
    if suplente:
        suplente.calidad = Jurado.Calidad.TITULAR
        suplente.version += 1
        suplente.actualizado_por = usuario
        suplente.full_clean()
        suplente.save(update_fields=["calidad", "version", "actualizado_por", "actualizado_en"])
        ActuacionJurado.objects.create(
            concurso_id=concurso_id, jurado=suplente, tipo="promocion",
            representacion=suplente.representacion, calidad_anterior=Jurado.Calidad.SUPLENTE,
            calidad_nueva=Jurado.Calidad.TITULAR, fecha_actuacion=fecha_resolucion,
            resolucion=resolucion, fojas=fojas, observaciones=observaciones,
            antecedente=presentacion, registrado_por=usuario,
        )
    return baja


@transaction.atomic
def designar_reemplazante(*, concurso, representacion, calidad, datos, usuario,
                          resolucion, fecha_resolucion, fojas="", observaciones=""):
    _autorizado(usuario)
    if not resolucion.strip():
        raise ValidationError("La resolución rectoral es obligatoria para una nueva designación.")
    Concurso.objects.select_for_update().get(pk=concurso.pk)
    if Jurado.objects.filter(concurso=concurso, representacion=representacion, calidad=calidad).exists():
        raise ValidationError("La plaza todavía está ocupada. Primero registrá el cese formal del integrante.")
    if not plaza_con_antecedentes(concurso=concurso, representacion=representacion, calidad=calidad):
        raise ValidationError("La plaza todavía no tiene antecedentes: usá Agregar integrante para la designación inicial.")
    entrada = {**datos, "representacion": representacion, "calidad": calidad}
    jurado = crear_participacion(modelo=Jurado, concurso=concurso, datos=entrada,
                                  usuario=usuario, permitir_reemplazo=True)
    ActuacionJurado.objects.create(
        concurso=concurso, jurado=jurado, tipo="designacion",
        representacion=representacion, calidad_nueva=calidad,
        fecha_actuacion=fecha_resolucion, resolucion=resolucion,
        fojas=fojas, observaciones=observaciones, registrado_por=usuario,
    )
    return jurado
