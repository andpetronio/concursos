"""Escala aplicada al dictamen ordinario: sin desempeño laboral (art. 52).

Los 51 puntos de oposición se registran DIRECTAMENTE. No se convierte
una calificación expresada sobre 60 sin respaldo del acta del jurado.
La proporcionalidad 34/51 debe ser validada con el criterio institucional.
"""
from decimal import Decimal

from .models import Aspirante, EvaluacionAspirante

MAX_ANTECEDENTES = Decimal("34.00")
MAX_OPOSICION = Decimal("51.00")
MAX_TOTAL = MAX_ANTECEDENTES + MAX_OPOSICION
MINIMO_MERITO = MAX_TOTAL / 2
ESCALA_CODIGO = "sin-desempeno-34-51-v1"


def cuadro_resultados(concurso, *, bloquear=False):
    """Puestos solo cuando el orden es inequívoco. No desempata por DNI/PK."""
    consulta = Aspirante.objects.filter(concurso=concurso).select_related("persona", "evaluacion")
    consulta = consulta.order_by("persona__apellido", "persona__nombre", "pk")
    if bloquear:
        consulta = consulta.select_for_update(of=("self",))
    postulantes = list(consulta)
    pendientes, elegibles, insuficientes = [], [], []
    for aspirante in postulantes:
        try:
            evaluacion = aspirante.evaluacion
        except EvaluacionAspirante.DoesNotExist:
            pendientes.append(f"{aspirante.persona.apellido}, {aspirante.persona.nombre}")
            continue
        total = evaluacion.total
        fila = {
            "aspirante_id": aspirante.pk,
            "apellido": aspirante.persona.apellido,
            "nombre": aspirante.persona.nombre,
            "dni": aspirante.persona.dni,
            "antecedentes": f"{evaluacion.antecedentes:.2f}",
            "oposicion": f"{evaluacion.oposicion:.2f}",
            "total": f"{total:.2f}",
            "version_evaluacion": evaluacion.version,
        }
        (elegibles if total >= MINIMO_MERITO else insuficientes).append(fila)
    elegibles.sort(key=lambda fila: (-Decimal(fila["total"]), -Decimal(fila["oposicion"])))
    insuficientes.sort(key=lambda fila: (-Decimal(fila["total"]), -Decimal(fila["oposicion"])))
    empates = []
    for indice, fila in enumerate(elegibles):
        if indice and (fila["total"], fila["oposicion"]) == (elegibles[indice - 1]["total"], elegibles[indice - 1]["oposicion"]):
            empates.append(f"{elegibles[indice - 1]['apellido']}, {elegibles[indice - 1]['nombre']} y {fila['apellido']}, {fila['nombre']}")
    for indice, fila in enumerate(elegibles):
        fila["puesto"] = indice + 1 if not empates else None
    return {
        "escala": {"codigo": ESCALA_CODIGO, "antecedentes": str(MAX_ANTECEDENTES),
                   "oposicion": str(MAX_OPOSICION), "total": str(MAX_TOTAL), "minimo": str(MINIMO_MERITO),
                   "desempeno": "No aplicable (artículo 52, Ordenanza 33/10-CS)"},
        "cantidad_aspirantes": len(postulantes),
        "orden_merito": elegibles,
        "puntaje_insuficiente": insuficientes,
        "evaluaciones_pendientes": pendientes,
        "empates_pendientes": empates,
    }


def faltantes_resultados(cuadro):
    faltantes = [f"Registrar evaluación de antecedentes y oposición: {nombre}."
                for nombre in cuadro["evaluaciones_pendientes"]]
    if not cuadro["orden_merito"]:
        if not cuadro["cantidad_aspirantes"]:
            faltantes.append("No hay aspirantes registrados: verificar el acta de inscriptos y tramitar, si corresponde, la declaración de concurso desierto (artículo 45).")
        elif not cuadro["evaluaciones_pendientes"]:
            faltantes.append("Todos los aspirantes evaluados quedaron debajo de 42,50/85: no corresponde generar una aprobación ordinaria con orden de mérito; revisar la declaración por insuficiencia de méritos (artículo 45).")
    for empate in cuadro["empates_pendientes"]:
        faltantes.append(f"Empate no resuelto según el artículo 41: {empate}.")
    return faltantes


# La nueva modalidad es sugerida para un nuevo LLAMADO, nunca asignada al
# concurso existente. Los acotados y los abiertos requieren otro tratamiento.
_MODALIDAD_SIGUIENTE = {
    "cerrado_interno": ("cerrado_general", "Cerrado General"),
    "cerrado_general": ("abierto", "Abierto"),
}


def diagnostico_sin_ganador(concurso, *, cuadro=None, acta_inscriptos_completa=None):
    """Sugiere un resultado operativo; NO declara desierto ni crea convocatoria.

    La Ordenanza 33/10-CS, art. 45 (mod. 21/13-CS), denomina «desierto»
    tanto a la falta de aspirantes como a la insuficiencia de méritos.
    «Fracasado» se reserva aquí como distinción OPERATIVA, no como nombre
    jurídico automático de la resolución.
    """
    cuadro = cuadro if cuadro is not None else cuadro_resultados(concurso)
    cantidad = cuadro["cantidad_aspirantes"]
    if cantidad == 0:
        # Una inscripción todavía no cargada NO prueba la inexistencia de
        # inscriptos. Hace falta el acta verificada con su foja válida.
        if acta_inscriptos_completa is None:
            control = concurso.controles_documentales.filter(requisito="acta_inscriptos").first()
            acta_inscriptos_completa = bool(control and control.completo)
        if not acta_inscriptos_completa:
            return None
        codigo = "desierto_sin_inscriptos"
        titulo = "Sin inscriptos: posible concurso desierto"
        explicacion = "El acta de inscriptos está verificada y no hay aspirantes registrados. Corresponde revisar el trámite de declaración por falta de aspirantes."
    elif not cuadro["evaluaciones_pendientes"] and not cuadro["orden_merito"]:
        codigo = "fracasado_por_merito"
        titulo = "Sin orden de mérito: insuficiencia de méritos"
        explicacion = "Ningún aspirante evaluado alcanza 42,50 puntos sobre 85. Operativamente se identifica como fracasado; el artículo 45 contempla la declaración de concurso desierto por insuficiencia de méritos."
    else:
        return None

    siguiente = _MODALIDAD_SIGUIENTE.get(concurso.modalidad)
    return {
        "codigo": codigo,
        "titulo": titulo,
        "explicacion": explicacion,
        "siguiente_codigo": siguiente[0] if siguiente else None,
        "siguiente_nombre": siguiente[1] if siguiente else None,
        "modalidad_sin_regla": not bool(siguiente),
        "referencia": "Artículo 45 del Anexo de la Ordenanza 33/10-CS (modificado por Ordenanza 21/13-CS)",
    }
