import re

from django.core.exceptions import ValidationError


def normalizar_fojas(valor):
    valor = str(valor).strip()
    if not valor:
        return ""
    partes = re.fullmatch(r"([0-9]+)\s*(?:/\s*([0-9]+))?", valor)
    if not partes:
        raise ValidationError("Ingresá una foja o un rango, por ejemplo 5 o 5/8.")
    inicio, final = partes.groups()
    # Acotar antes de int(): evita entradas desproporcionadas fuera del campo.
    if len(inicio) > 50 or (final is not None and len(final) > 50):
        raise ValidationError("La referencia de fojas es demasiado larga.")
    inicio = int(inicio)
    final = int(final) if final is not None else None
    if inicio < 1 or (final is not None and (final < 1 or inicio > final)):
        raise ValidationError("Las fojas deben ser positivas y el inicio no puede superar el final del rango.")
    return str(inicio) if final is None else f"{inicio}/{final}"


def normalizar_codigo_dos_digitos(valor):
    """Normaliza códigos de clasificación como texto, conservando el cero inicial."""
    from django.core.exceptions import ValidationError
    texto = (valor or "").strip()
    if not texto:
        return ""
    if not texto.isascii() or not texto.isdecimal() or len(texto) > 2:
        raise ValidationError("Ingresá uno o dos dígitos numéricos (por ejemplo, 01 o 12).")
    return texto.zfill(2)
