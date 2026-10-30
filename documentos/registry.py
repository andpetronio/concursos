"""Catálogo único de alcance y variables; ninguna fuente ausente se sustituye."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TipoDocumento:
    codigo: str
    nombre: str
    descripcion: str
    fuente: str
    automaticas: str
    complementarias: str
    pendientes: str
    version: str = ""


TIPOS = (
    TipoDocumento("elecciones", "Nota para elección de representantes del personal", "Solicitud preparatoria; no afirma elección ni designación.",
                  "Nota para elecciones por el estamento.docx.pdf", "Identificación del concurso y estructura",
                  "Jefatura de Personal configurada y antecedentes de vacancia del concurso", "Requiere jefatura de Personal, membrete y antecedentes acreditados", "elecciones-5"),
    TipoDocumento("convocatoria", "Proyecto de resolución de convocatoria", "Proyecto y anexo, sujeto a habilitación documental.",
                  "PROYECTO RES CONVOCATORIA.pdf", "Datos del concurso, seis jurados, actuaciones verificadas y fojas",
                  "Fecha de apertura; turno, domicilio, jurisdicción y presupuesto provienen del concurso", "Los complementos críticos faltantes bloquean la generación", "convocatoria-7"),
    TipoDocumento("jurados", "Notificaciones individuales a jurados", "Seis notas individuales editables, conservadas también en ZIP.",
                  "Modelo nota notificación Jurado.docx.pdf", "Concurso, persona, título, unidad, representación y carácter",
                  "Resolución oficial desde la ficha del concurso; fecha automática de preparación", "La resolución oficial debe estar emitida; generar la nota no acredita notificación", "jurados-5"),
    TipoDocumento("apunsj", "Oficio a APUNSJ solicitando veedor", "Solicitud de datos de veedor según el modelo institucional.",
                  "solicitar veedor.docx", "Concurso, resolución oficial, destinatario APUNSJ y membrete vigente",
                  "Sin datos complementarios: fecha automática y resolución desde la ficha", "Requiere resolución oficial de convocatoria registrada", "apunsj-3"),
    TipoDocumento("dictamen", "Proyecto de resolución de aprobación del dictamen", "Sin presunción de resultados ni hechos administrativos.",
                  "PROYECTO RES. APROBANDO DICTAMEN.docx", "Concurso, jurados, aspirantes y actuaciones verificadas",
                  "Puntajes estructurados /34 y /51, fechas y autoridad del sorteo, confirmaciones expresas", "La evaluación de todos los aspirantes y el orden sin empates pendientes son obligatorios", "dictamen-fuente-1"),
    TipoDocumento("sorteo_acta", "Acta de sorteo de temas", "Acta editable con autoridad fiscalizadora, jurados, aspirantes y veeduría presentes.",
                  "Acta de sorteo de temas.docx", "Concurso, jurados, aspirantes y resolución oficial de convocatoria",
                  "Fecha y hora, autoridad fiscalizadora, asistentes, resultado del sorteo y prueba de oposición",
                  "Requiere convocatoria oficial, jurado y acta de valoración de antecedentes acreditada", "sorteo-acta-fuente-2"),
    TipoDocumento("desierto_inscriptos", "Proyecto de resolución declarando desierto el concurso por falta de aspirantes",
                  "Declaración por ausencia de inscriptos y trámite del próximo llamado; no constituye una nueva convocatoria.",
                  "", "Identificación y cargo del concurso, resolución oficial, acta de inscripción verificada y fojas",
                  "Confirmación del operador de que el acta acredita cero inscriptos",
                  "Requiere acta verificada, ausencia de aspirantes registrados y modalidad que permita nuevo llamado",
                  "desierto-inscriptos-1"),
    TipoDocumento("designacion", "Proyecto de resolución de designación", "Sin selección automática de aspirante ni efectos administrativos.",
                  "PROYECTO RES. DESIGNACION.docx", "Concurso y antecedentes documentales verificados",
                  "Persona propuesta, mérito, antecedentes, limitación opcional y presupuesto acreditados", "Los antecedentes y complementos críticos son obligatorios", "designacion-fuente-1"),

)
POR_CODIGO = {tipo.codigo: tipo for tipo in TIPOS}


def nombre_miembro(indice):
    """Nombres internos fijos: no se aceptan rutas ni nombres de personas."""
    if indice not in range(1, 7):
        raise ValueError("Índice de notificación inválido")
    return f"jurado-{indice}.docx"
