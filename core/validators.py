"""Formatos administrativos compartidos. Los identificadores siempre son texto."""
import re

from django.core.exceptions import ValidationError


DNI_ERROR = "Ingresá un DNI de exactamente 8 dígitos (99.999.999)."
EXPEDIENTE_ERROR = "Ingresá un expediente como 01-758-2026: 2 dígitos, un número entre 1 y 9999 y 4 dígitos."


def normalizar_dni(valor):
    valor = str(valor).strip()
    # Se conservan los separadores admitidos por la versión anterior.
    if not re.fullmatch(r"[0-9.\s-]+", valor):
        raise ValidationError(DNI_ERROR)
    dni = re.sub(r"[.\s-]", "", valor)
    if not re.fullmatch(r"[0-9]{8}", dni):
        raise ValidationError(DNI_ERROR)
    return dni


def validar_expediente(valor):
    if not re.fullmatch(r"[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}", valor):
        raise ValidationError(EXPEDIENTE_ERROR)
    return valor


def validar_cambio(instance, campo, normalizar):
    """No exige corregir un identificador histórico para editar otros datos."""
    valor = getattr(instance, campo)
    try:
        return normalizar(valor)
    except ValidationError:
        if instance.pk and type(instance).objects.filter(pk=instance.pk, **{campo: valor}).exists():
            return valor
        raise


TELEFONO_ERROR = "Ingresá 10 dígitos con el formato 999-9999999."
CODIGO_PRESUPUESTARIO_ERROR = "El código presupuestario no puede superar los 5 caracteres."


def normalizar_telefono(valor):
    """Permite diez dígitos pegados o el formato visible; no inventa prefijos."""
    valor = str(valor).strip()
    if re.fullmatch(r"[0-9]{10}", valor):
        return f"{valor[:3]}-{valor[3:]}"
    if not re.fullmatch(r"[0-9]{3}-[0-9]{7}", valor):
        raise ValidationError(TELEFONO_ERROR)
    return valor


def validar_codigo_presupuestario(valor):
    if len(str(valor)) > 5:
        raise ValidationError(CODIGO_PRESUPUESTARIO_ERROR)
    return valor
