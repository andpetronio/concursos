"""F4M.2: lectura de antecedentes del jurado para revisión, sin emitir documentos."""

from django import forms
from django.views.generic import DetailView

from concursos.models import Concurso
from concursos.views import AccesoConcursoMixin

from .jurados_considerandos import preparar_antecedentes_jurado
from .models import ActuacionJurado


class FechaDocumentoJuradoForm(forms.Form):
    fecha_documento = forms.DateField(
        label="Fecha del documento a preparar",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=(
            "Opcional. Muestra resoluciones fechadas hasta ese día; "
            "no certifica desde cuándo producen efectos."
        ),
    )


class ConsiderandosJuradoPreviewView(AccesoConcursoMixin, DetailView):
    """Vista de solo lectura. No modifica las actuaciones ni los borradores DOCX."""

    model = Concurso
    permission_required = "concursos.view_concurso"
    template_name = "participantes/considerandos_jurado.html"
    context_object_name = "concurso"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        con_fecha = "fecha_documento" in self.request.GET
        formulario = FechaDocumentoJuradoForm(self.request.GET if con_fecha else None)
        context["formulario_fecha"] = formulario

        # Si la fecha es inválida, mostrar el error sin sustituirla por la fecha
        # actual ni presentar como válidos antecedentes de otro período.
        if con_fecha and not formulario.is_valid():
            context["vista_previa"] = None
            return context

        fecha = formulario.cleaned_data["fecha_documento"] if con_fecha else None
        actuaciones = list(ActuacionJurado.objects.filter(
            concurso=self.object,
        ).select_related("jurado__persona", "antecedente", "resuelto_por"))
        context["cantidad_actuaciones_jurado"] = len(actuaciones)
        context["vista_previa"] = preparar_antecedentes_jurado(
            actuaciones, fecha_documento=fecha,
        )
        context["fecha_documento_seleccionada"] = fecha
        return context
