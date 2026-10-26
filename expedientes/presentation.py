from .catalogo import REQUISITOS, SECCIONES
from .forms import ControlDocumentalForm, EtapaDocumentalForm
from .services import consultar_documentacion


def estado_de_control(control, *, secciones_exigibles):
    """Estado visible único para la ficha y las respuestas de guardado automático."""
    requisito = control.definicion
    if control.completo:
        return "Verificado", "completo"
    if control.verificado:
        return "Foja pendiente", "foja"
    if requisito.seccion in secciones_exigibles:
        return "Pendiente exigible", "exigible"
    if control.version > 1:
        return "Sin verificar", "sin-verificar"
    return "No registrado", "no-registrado"


def contexto_documental(concurso, *, jurados, error=None, error_etapa=None):
    documentacion = consultar_documentacion(concurso, jurados=jurados)
    controles = {c.requisito: c for c in documentacion.controles}
    grupos = {codigo: [] for codigo, _ in SECCIONES}
    for numero, requisito in enumerate(REQUISITOS, start=1):
        control = controles.get(requisito.codigo)
        if control is None:
            continue
        estado, estado_clase = estado_de_control(control, secciones_exigibles=documentacion.secciones_exigibles)
        formulario = error[1] if error and error[0] == control.pk else ControlDocumentalForm(
            instance=control, prefix=f"control-{control.pk}",
        )
        grupos[requisito.seccion].append({
            "numero": numero, "control": control, "requisito": requisito, "estado": estado, "form": formulario,
            "estado_clase": estado_clase,
        })
    return {
        "documentacion": documentacion,
        "form_etapa_documental": error_etapa or EtapaDocumentalForm(instance=documentacion.seguimiento, prefix="etapa"),
        "secciones_documentales": [{"codigo": codigo, "nombre": nombre, "filas": grupos[codigo],
                                     "completos": sum(fila["control"].completo for fila in grupos[codigo]),
                                     "total": len(grupos[codigo])}
                                    for codigo, nombre in SECCIONES],
    }
