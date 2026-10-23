from .catalogo import REQUISITOS, SECCIONES
from .forms import ControlDocumentalForm, EtapaDocumentalForm
from .services import consultar_documentacion


def contexto_documental(concurso, *, jurados, error=None, error_etapa=None):
    documentacion = consultar_documentacion(concurso, jurados=jurados)
    controles = {c.requisito: c for c in documentacion.controles}
    grupos = {codigo: [] for codigo, _ in SECCIONES}
    for numero, requisito in enumerate(REQUISITOS, start=1):
        control = controles.get(requisito.codigo)
        if control is None:
            continue
        if control.completo:
            estado = "Verificado"
        elif control.verificado:
            estado = "Foja pendiente"
        elif requisito.seccion in documentacion.secciones_exigibles:
            estado = "Pendiente exigible"
        elif control.version > 1:
            estado = "Sin verificar"
        else:
            estado = "No registrado"
        formulario = error[1] if error and error[0] == control.pk else ControlDocumentalForm(
            instance=control, prefix=f"control-{control.pk}",
        )
        grupos[requisito.seccion].append({
            "numero": numero, "control": control, "requisito": requisito, "estado": estado, "form": formulario,
        })
    return {
        "documentacion": documentacion,
        "form_etapa_documental": error_etapa or EtapaDocumentalForm(instance=documentacion.seguimiento, prefix="etapa"),
        "secciones_documentales": [{"codigo": codigo, "nombre": nombre, "filas": grupos[codigo]}
                                    for codigo, nombre in SECCIONES],
    }
