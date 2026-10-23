from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CambioEstado, Concurso


def comprobar_version(concurso, version_esperada):
    if concurso.version != version_esperada:
        raise ValidationError("Otro operador modificó el concurso. Volvé a abrir la ficha y revisá los datos antes de guardar.")


@transaction.atomic
def crear_concurso(*, datos, usuario):
    concurso = Concurso(
        **{campo: datos.get(campo, "") for campo in Concurso.DATOS_EDITABLES},
        tramo=datos.get("tramo", ""),
        creado_por=usuario, actualizado_por=usuario,
    )
    concurso.full_clean()
    concurso.save()
    from expedientes.services import inicializar_controles
    inicializar_controles(concurso)
    CambioEstado.objects.create(concurso=concurso, usuario=usuario,
                                estado_nuevo=concurso.estado, situacion_nueva=concurso.situacion)
    return concurso


@transaction.atomic
def editar_concurso(*, pk, datos, usuario, version_esperada):
    concurso = Concurso.objects.select_for_update().get(pk=pk)
    comprobar_version(concurso, version_esperada)
    for campo in Concurso.DATOS_EDITABLES:
        setattr(concurso, campo, datos[campo])
    concurso.tramo = datos.get("tramo", "")
    concurso.actualizado_por = usuario
    concurso.version += 1
    concurso.full_clean()
    concurso.save()
    return concurso


@transaction.atomic
def cambiar_estado(*, pk, estado, situacion, justificacion, usuario, version_esperada):
    concurso = Concurso.objects.select_for_update().get(pk=pk)
    comprobar_version(concurso, version_esperada)
    if (estado, situacion) == (concurso.estado, concurso.situacion):
        raise ValidationError("Elegí un estado o una situación diferente de los actuales.")
    cambio = CambioEstado(concurso=concurso, usuario=usuario,
                           estado_anterior=concurso.estado, estado_nuevo=estado,
                           situacion_anterior=concurso.situacion, situacion_nueva=situacion,
                           justificacion=justificacion)
    concurso.estado = estado
    concurso.situacion = situacion
    # Valida los valores de estado persistentes; el servicio nunca decide transiciones.
    cambio.full_clean()
    concurso.actualizado_por = usuario
    concurso.version += 1
    concurso.save()
    cambio.save()
    return concurso
