from django.core.exceptions import ValidationError
from django.db import transaction
from core.validators import normalizar_dni, validar_cambio

from .models import Persona


@transaction.atomic
def crear_participacion(*, modelo, concurso, datos, usuario, persona_id=None):
    identidad = {campo: datos[campo] for campo in ("apellido", "nombre", "dni")}
    identidad["dni"] = normalizar_dni(identidad["dni"])
    if persona_id is not None:
        persona = Persona.objects.select_for_update().get(pk=persona_id)
    else:
        persona, _ = Persona.objects.select_for_update().get_or_create(
            dni=identidad["dni"], defaults={
                **{campo: identidad[campo] for campo in ("apellido", "nombre")},
                "creado_por": usuario, "actualizado_por": usuario,
            },
        )
    if (persona.dni, persona.apellido.casefold(), persona.nombre.casefold()) != (
        identidad["dni"], identidad["apellido"].casefold(), identidad["nombre"].casefold()
    ):
        raise ValidationError("La identidad registrada cambió. Volvé a abrir el formulario y revisá los datos antes de vincularla.")
    participacion = modelo(
        concurso=concurso, persona=persona, creado_por=usuario, actualizado_por=usuario,
        **{campo: valor for campo, valor in datos.items() if campo not in identidad},
    )
    participacion.full_clean()
    participacion.save()
    return participacion


def comprobar_version(registro, version_esperada):
    if registro.version != version_esperada:
        raise ValidationError("Otro operador modificó este registro. Volvé a abrir el formulario y revisá los datos antes de guardar.")


@transaction.atomic
def editar_participacion(*, participacion, datos, usuario, version_esperada):
    participacion = type(participacion).objects.select_for_update().get(pk=participacion.pk)
    comprobar_version(participacion, version_esperada)
    for campo, valor in datos.items():
        setattr(participacion, campo, valor)
    participacion.actualizado_por = usuario
    participacion.version += 1
    participacion.full_clean()
    participacion.save()
    return participacion


@transaction.atomic
def editar_persona(*, persona, datos, usuario, version_esperada):
    persona = Persona.objects.select_for_update().get(pk=persona.pk)
    comprobar_version(persona, version_esperada)
    datos = dict(datos)
    anterior = persona.dni
    persona.dni = datos["dni"]
    datos["dni"] = validar_cambio(persona, "dni", normalizar_dni)
    persona.dni = anterior
    if datos["dni"] != persona.dni:
        from .models import Aspirante, Jurado, Veedor

        concursos = set()
        for model in (Jurado, Veedor, Aspirante):
            concursos.update(model.objects.filter(persona=persona).values_list("concurso_id", flat=True))
        if len(concursos) > 1:
            raise ValidationError("No se puede cambiar el DNI de una persona vinculada a varios concursos.")
    for campo, valor in datos.items():
        setattr(persona, campo, valor)
    persona.actualizado_por = usuario
    persona.version += 1
    persona.full_clean()
    persona.save()
    return persona


@transaction.atomic
def guardar_evaluacion(*, aspirante, antecedentes, oposicion, usuario, version_esperada, motivo=""):
    """Bloquea la inscripción: alta doble y edición simultánea son incompatibles."""
    from .models import Aspirante, EvaluacionAspirante, CambioEvaluacion
    if not usuario.has_perms(("concursos.view_concurso", "concursos.change_concurso")):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    locked = Aspirante.objects.select_for_update().get(pk=aspirante.pk)
    actual = EvaluacionAspirante.objects.select_for_update().filter(aspirante=locked).first()
    version = actual.version if actual else 0
    if version != version_esperada:
        raise ValidationError("Otro operador modificó esta evaluación. Volvé a abrir el formulario antes de guardar.")
    if actual and (actual.antecedentes != antecedentes or actual.oposicion != oposicion) and not motivo.strip():
        raise ValidationError("Indicá el motivo de la corrección de puntajes para conservar su trazabilidad.")
    if actual and (actual.antecedentes, actual.oposicion) == (antecedentes, oposicion):
        return actual
    antes_a = actual.antecedentes if actual else None
    antes_o = actual.oposicion if actual else None
    evaluacion = actual or EvaluacionAspirante(aspirante=locked, creado_por=usuario)
    evaluacion.antecedentes = antecedentes
    evaluacion.oposicion = oposicion
    evaluacion.actualizado_por = usuario
    evaluacion.version = version + 1
    evaluacion.full_clean()
    evaluacion.save()
    CambioEvaluacion.objects.create(
        evaluacion=evaluacion, antecedentes_antes=antes_a, oposicion_antes=antes_o,
        antecedentes_despues=antecedentes, oposicion_despues=oposicion,
        motivo=motivo.strip(), version=evaluacion.version, usuario=usuario,
    )
    return evaluacion
