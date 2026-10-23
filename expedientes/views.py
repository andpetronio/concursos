from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView

from concursos.views import AccesoConcursoMixin, ConcursoDetailView

from .forms import ControlDocumentalForm, EtapaDocumentalForm
from .models import ControlDocumental, SeguimientoDocumental
from .services import actualizar_control, actualizar_etapa


class ControlDocumentalUpdateView(ConcursoDetailView):
    permission_required = ("concursos.view_concurso", "expedientes.change_controldocumental")
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        control = get_object_or_404(ControlDocumental, pk=kwargs["control_id"], concurso=self.object)
        form = ControlDocumentalForm(request.POST, instance=control, prefix=f"control-{control.pk}")
        if form.is_valid():
            try:
                actualizar_control(
                    concurso_id=self.object.pk, control_id=control.pk, datos=form.cleaned_data,
                    usuario=request.user, version_esperada=form.cleaned_data["version_esperada"],
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "El control documental se guardó correctamente.")
                return redirect(f"{self.object.get_absolute_url()}#documental-{control.pk}")
        self.documental_error = (control.pk, form)
        return self.render_to_response(self.get_context_data())


class HistorialControlView(AccesoConcursoMixin, ListView):
    permission_required = "concursos.view_concurso"
    template_name = "expedientes/historial.html"
    paginate_by = 20

    def get_queryset(self):
        self.control = get_object_or_404(
            ControlDocumental.objects.select_related("concurso"),
            pk=self.kwargs["control_id"], concurso_id=self.kwargs["pk"],
        )
        return self.control.historial.select_related("usuario")

    def get_context_data(self, **kwargs):
        return super().get_context_data(control=self.control, concurso=self.control.concurso, **kwargs)


class EtapaDocumentalUpdateView(ConcursoDetailView):
    permission_required = ("concursos.view_concurso", "expedientes.change_controldocumental")
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        seguimiento = get_object_or_404(SeguimientoDocumental, concurso=self.object)
        form = EtapaDocumentalForm(request.POST, instance=seguimiento, prefix="etapa")
        if form.is_valid():
            try:
                actualizar_etapa(concurso_id=self.object.pk, etapa=form.cleaned_data["etapa"], usuario=request.user,
                                 version_esperada=form.cleaned_data["version_esperada"])
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "La etapa documental se guardó correctamente.")
                return redirect(f"{self.object.get_absolute_url()}#control-documental")
        self.documental_error_etapa = form
        return self.render_to_response(self.get_context_data())


class HistorialEtapaView(AccesoConcursoMixin, ListView):
    permission_required = "concursos.view_concurso"
    template_name = "expedientes/historial_etapa.html"
    paginate_by = 20

    def get_queryset(self):
        self.seguimiento = get_object_or_404(SeguimientoDocumental.objects.select_related("concurso"),
                                            concurso_id=self.kwargs["pk"])
        return self.seguimiento.historial.select_related("usuario")

    def get_context_data(self, **kwargs):
        return super().get_context_data(concurso=self.seguimiento.concurso, **kwargs)
