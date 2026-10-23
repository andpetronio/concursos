"""Copia local versionada de CoPla: datos/agrupamientos_iniciales.json y DEC-054.

No importa código de CoPla ni consulta su base. Ver trazabilidad en DECISIONES.
"""
import json
from pathlib import Path

from django.core.exceptions import ValidationError


CATALOGO_CARGOS = json.loads((Path(__file__).parent / "data" / "clasificacion_cargos.json").read_text(encoding="utf-8"))
AGRUPAMIENTOS = [(codigo, f"{codigo} — {datos['denominacion']}") for codigo, datos in CATALOGO_CARGOS.items()]
CATEGORIAS = [(str(numero), str(numero)) for numero in range(1, 8)]


def categorias_para(agrupamiento):
    tramos = CATALOGO_CARGOS.get(agrupamiento, {}).get("tramos", {})
    return [str(numero) for numero in sorted({n for categorias in tramos.values() for n in categorias})]


def tramo_para(agrupamiento, categoria):
    for tramo, categorias in CATALOGO_CARGOS.get(agrupamiento, {}).get("tramos", {}).items():
        if str(categoria) in [str(numero) for numero in categorias]:
            return tramo
    raise ValidationError("La categoría no está habilitada para el agrupamiento seleccionado.")


def opciones_dependientes():
    """La UI recibe la matriz ya resuelta por Python: no mantiene reglas paralelas."""
    return {codigo: [{"categoria": categoria, "tramo": tramo_para(codigo, categoria)}
                     for categoria in categorias_para(codigo)] for codigo in CATALOGO_CARGOS}
