from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from . import services
from .forms import CambioEstadoForm, ConcursoForm, FiltroConcursosForm
from .models import Concurso


def advertir_expediente_repetido(request, concurso):
    if Concurso.objects.filter(expediente=concurso.expediente).exclude(pk=concurso.pk).exists():
        messages.warning(request, "El número de expediente ya está registrado en otro concurso. Se guardaron los datos; revisá que corresponda.")


class AccesoConcursoMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, "core/forbidden.html", {
                "description": "Tu cuenta no tiene los permisos necesarios para esta operación sobre concursos.",
            }, status=403)
        return super().handle_no_permission()


class ConcursoListView(AccesoConcursoMixin, ListView):
    model = Concurso
    permission_required = "concursos.view_concurso"
    template_name = "concursos/lista.html"
    context_object_name = "concursos"
    paginate_by = 20

    def get_queryset(self):
        self.filtros = FiltroConcursosForm(self.request.GET)
        queryset = super().get_queryset()
        if not self.filtros.is_valid():
            return queryset.none()
        if q := self.filtros.cleaned_data["q"]:
            queryset = queryset.filter(Q(expediente__icontains=q) | Q(denominacion__icontains=q)
                                       | Q(funciones__icontains=q) | Q(codigo_presupuestario__icontains=q))
        if estado := self.filtros.cleaned_data["estado"]:
            queryset = queryset.filter(estado=estado)
        return queryset

    def get_context_data(self, **kwargs):
        return super().get_context_data(filtros=self.filtros, **kwargs)


class ConcursoDetailView(AccesoConcursoMixin, DetailView):
    model = Concurso
    permission_required = "concursos.view_concurso"
    template_name = "concursos/detalle.html"
    context_object_name = "concurso"

    def get_queryset(self):
        return super().get_queryset().select_related("creado_por", "actualizado_por")

    def get_context_data(self, **kwargs):
        from participantes.models import Aspirante, Jurado, Veedor

        context = super().get_context_data(**kwargs)
        context["datos_concurso"] = [
            (self.object._meta.get_field(campo).verbose_name.capitalize(),
             getattr(self.object, f"get_{campo}_display", lambda: getattr(self.object, campo))())
            for campo in (*Concurso.DATOS_EDITABLES, "tramo")
        ]
        context["page_obj"] = Paginator(self.object.historial.select_related("usuario"), 20).get_page(
            self.request.GET.get("page")
        )
        context["jurados"] = Jurado.objects.filter(concurso=self.object).select_related("persona")
        context["veedores"] = Veedor.objects.filter(concurso=self.object).select_related("persona")
        context["aspirantes"] = Aspirante.objects.filter(concurso=self.object).select_related("persona")
        from expedientes.presentation import contexto_documental
        context["jurados"] = list(context["jurados"])
        context.update(contexto_documental(self.object, jurados=context["jurados"],
                                          error=getattr(self, "documental_error", None),
                                          error_etapa=getattr(self, "documental_error_etapa", None)))
        from documentos.services import contexto_documentos
        context.update(contexto_documentos(self.object))
        return context


class ConcursoCreateView(AccesoConcursoMixin, CreateView):
    model = Concurso
    form_class = ConcursoForm
    permission_required = ("concursos.view_concurso", "concursos.add_concurso")
    template_name = "concursos/formulario.html"
    extra_context = {"title": "Registrar concurso"}

    def form_valid(self, form):
        self.object = services.crear_concurso(datos=form.cleaned_data, usuario=self.request.user)
        advertir_expediente_repetido(self.request, self.object)
        messages.success(self.request, "El concurso se registró correctamente.")
        return redirect(self.object)


class ConcursoUpdateView(AccesoConcursoMixin, UpdateView):
    model = Concurso
    form_class = ConcursoForm
    permission_required = ("concursos.view_concurso", "concursos.change_concurso")
    template_name = "concursos/formulario.html"
    extra_context = {"title": "Editar concurso"}

    def form_valid(self, form):
        try:
            self.object = services.editar_concurso(pk=self.object.pk, datos=form.cleaned_data,
                                                   usuario=self.request.user,
                                                   version_esperada=form.cleaned_data["version_esperada"])
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Los datos del concurso se actualizaron correctamente.")
        advertir_expediente_repetido(self.request, self.object)
        return redirect(self.object)


class CambioEstadoView(AccesoConcursoMixin, FormView):
    form_class = CambioEstadoForm
    permission_required = ("concursos.view_concurso", "concursos.cambiar_estado_concurso")
    template_name = "concursos/estado.html"

    def get_concurso(self):
        if not hasattr(self, "concurso"):
            self.concurso = get_object_or_404(Concurso, pk=self.kwargs["pk"])
        return self.concurso

    def get_initial(self):
        concurso = self.get_concurso()
        inicial = {"estado": concurso.estado, "situacion": concurso.situacion, "version_esperada": concurso.version}
        if self.request.GET.get("sugerencia") == "dictamen":
            from expedientes.services import sugerencia_estado
            propuesta = sugerencia_estado(concurso, concurso.controles_documentales.all())
            if propuesta:
                inicial.update(estado=propuesta, justificacion="Confirmación de sugerencia por dictamen documental verificado.")
        return inicial

    def get_context_data(self, **kwargs):
        return super().get_context_data(concurso=self.get_concurso(), **kwargs)

    def form_valid(self, form):
        try:
            concurso = services.cambiar_estado(pk=self.get_concurso().pk, usuario=self.request.user,
                                               **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "El cambio de estado y situación quedó registrado en el historial.")
        return redirect(concurso)
