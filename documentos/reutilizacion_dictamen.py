"""Sugerencias editables para el borrador de dictamen.

Un DOCX conservado es un *borrador*, no una actuación acreditada. Sus datos
pueden evitar volver a tipear fechas y nombres, pero nunca acreditan hechos
ni autorizan a marcar confirmaciones en nombre del operador.
"""
from datetime import date, time

from .models import GeneracionDocumento


CAMPOS_ACTA_SORTEO = (
    "fecha_sorteo_tema", "hora_sorteo_tema",
    "fecha_oposicion", "hora_oposicion",
    "autoridad_tratamiento", "autoridad_cargo", "autoridad_nombre",
)
CAMPOS_FECHA = {"fecha_sorteo_tema", "fecha_oposicion"}
CAMPOS_HORA = {"hora_sorteo_tema", "hora_oposicion"}


def sugerencias_dictamen(concurso):
    """Último borrador del acta del *mismo* concurso, sin suponer validez oficial.

    Se recuperan únicamente campos de texto conocidos y se normalizan fechas
    y horas ISO. Nada procedente de otro documento se utiliza como confirmación.
    """
    if not concurso or not concurso.pk:
        return {}, None
    origen = (GeneracionDocumento.objects.filter(concurso=concurso, tipo="sorteo_acta")
              .only("pk", "generado_en", "instantanea").first())
    if origen is None:
        return {}, None
    datos = (origen.instantanea or {}).get("complementarios", {})
    if not isinstance(datos, dict):
        return {}, None
    sugeridos = {}
    for nombre in CAMPOS_ACTA_SORTEO:
        valor = datos.get(nombre)
        if not isinstance(valor, str) or not valor.strip():
            continue
        valor = valor.strip()
        try:
            if nombre in CAMPOS_FECHA:
                valor = date.fromisoformat(valor).isoformat()
            elif nombre in CAMPOS_HORA:
                valor = time.fromisoformat(valor).strftime("%H:%M")
            elif len(valor) > (50 if nombre == "autoridad_tratamiento" else
                              200 if nombre == "autoridad_cargo" else 250):
                continue
        except ValueError:
            continue
        sugeridos[nombre] = valor
    return sugeridos, origen if sugeridos else None


def grupos_campos_dictamen(formulario):
    """Una sola clasificación para la ficha y la revisión clásica."""
    reutilizados, pendientes, confirmaciones = [], [], []
    sugeridos = getattr(formulario, "sugerencias_dictamen", {})
    for campo in formulario.visible_fields():
        if campo.name == "revision_administrativa" or campo.name.startswith("presupuesto_"):
            continue
        if campo.field.widget.input_type == "checkbox":
            confirmaciones.append(campo)
        elif campo.name in sugeridos:
            reutilizados.append(campo)
        else:
            pendientes.append(campo)
    return {
        "reutilizados": reutilizados,
        "pendientes": pendientes,
        "confirmaciones": confirmaciones,
        "origen": getattr(formulario, "origen_sugerencias_dictamen", None),
    }
