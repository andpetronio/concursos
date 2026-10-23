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
