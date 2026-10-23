"""Catálogo ordinario aprobado en SDD-004: orden, sección y foja en una fuente."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Requisito:
    codigo: str
    nombre: str
    seccion: str
    requiere_foja: bool
    ayuda: str = ""


SECCIONES = (
    ("preparacion", "Preparación de convocatoria"),
    ("convocatoria", "Convocatoria"),
    ("inscripciones", "Inscripciones"),
    ("oposicion", "Antecedentes y oposición"),
    ("finalizacion", "Dictamen y finalización"),
)
REQUISITOS = (
    Requisito("jurado_dependencia", "Indicación de jurado titular y suplente por la dependencia convocante", "preparacion", True),
    Requisito("jurado_rectorado", "Indicación de jurado titular y suplente por el Rectorado", "preparacion", True),
    Requisito("jurado_personal", "Indicación de jurado titular y suplente por el personal de la dependencia", "preparacion", True),
    Requisito("afectacion_presupuestaria", "Afectación presupuestaria", "preparacion", True),
    Requisito("vacancia", "Certificación de vacancia del cargo", "preparacion", False),
    Requisito("publicacion_convocatoria", "Constancia de publicación de la resolución de convocatoria", "convocatoria", False),
    Requisito("oficio_apunsj", "Oficio a APUNSJ solicitando veedor", "convocatoria", False,
              "Controla el oficio de solicitud. La ausencia de un veedor designado no impide avanzar."),
    Requisito("notificacion_jurados", "Notas de notificación a jurados", "convocatoria", False,
              "Este único check acredita las notificaciones correspondientes a los seis jurados titulares y suplentes."),
    Requisito("acta_inscriptos", "Acta de inscriptos", "inscripciones", True),
    Requisito("envio_acta", "Constancia de envío del acta de inscriptos", "inscripciones", False),
    Requisito("entrega_jurado", "Constancia de entrega de la documentación al jurado", "inscripciones", False),
    Requisito("valoracion_antecedentes", "Acta de valoración de antecedentes", "oposicion", True),
    Requisito("nota_fechas", "Nota del jurado indicando fecha de sorteo de temas y prueba de oposición", "oposicion", True),
    Requisito("sorteo_temas", "Acta de sorteo de temas", "oposicion", True),
    Requisito("tres_temas", "Tres temas de examen", "oposicion", False),
    Requisito("asistencia_oposicion", "Planilla de asistencia a la prueba de oposición", "oposicion", False),
    Requisito("acta_oposicion", "Acta de prueba de oposición", "oposicion", True),
    Requisito("dictamen", "Dictamen del jurado", "finalizacion", True),
    Requisito("comunicacion_dictamen", "Constancia de comunicación del dictamen a los aspirantes", "finalizacion", False),
    Requisito("aprobacion_dictamen", "Resolución de aprobación del dictamen", "finalizacion", True),
    Requisito("designacion", "Resolución de designación", "finalizacion", True),
)
POR_CODIGO = {requisito.codigo: requisito for requisito in REQUISITOS}
OPCIONES_REQUISITO = [(r.codigo, r.nombre) for r in REQUISITOS]
