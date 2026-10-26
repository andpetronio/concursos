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
                  "PROYECTO RES. APROBANDO DICTAMEN.pdf", "Concurso, jurados, aspirantes y actuaciones verificadas",
                  "Evaluaciones, resultados, mérito, comunicaciones e impugnaciones acreditadas", "Los antecedentes y complementos críticos son obligatorios", "dictamen-3"),
    TipoDocumento("designacion", "Proyecto de resolución de designación", "Sin selección automática de aspirante ni efectos administrativos.",
                  "PROYECTO RES. DESIGNACION.pdf", "Concurso y antecedentes documentales verificados",
                  "Persona propuesta, mérito, efectos y condiciones acreditados", "Los antecedentes y complementos críticos son obligatorios", "designacion-3"),

)
POR_CODIGO = {tipo.codigo: tipo for tipo in TIPOS}


def nombre_miembro(indice):
    """Nombres internos fijos: no se aceptan rutas ni nombres de personas."""
    if indice not in range(1, 7):
        raise ValueError("Índice de notificación inválido")
    return f"jurado-{indice}.docx"
