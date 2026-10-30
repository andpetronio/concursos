from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string
from django.views.generic import ListView

from concursos.views import AccesoConcursoMixin, ConcursoDetailView

from .forms import ControlDocumentalForm, EtapaDocumentalForm
from .catalogo import SECCIONES
from .models import ControlDocumental, SeguimientoDocumental
from .presentation import estado_de_control
from .services import consultar_documentacion
from .services import actualizar_control, actualizar_etapa


class ControlDocumentalUpdateView(ConcursoDetailView):
    permission_required = ("concursos.view_concurso", "expedientes.change_controldocumental")
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        control = get_object_or_404(ControlDocumental, pk=kwargs["control_id"], concurso=self.object)
        form = ControlDocumentalForm(request.POST, instance=control, prefix=f"control-{control.pk}")
        auto = (request.headers.get("X-Requested-With") == "XMLHttpRequest"
                and "application/json" in request.headers.get("Accept", ""))
        if form.is_valid():
            try:
                control = actualizar_control(
                    concurso_id=self.object.pk, control_id=control.pk, datos=form.cleaned_data,
                    usuario=request.user, version_esperada=form.cleaned_data["version_esperada"],
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                if auto:
                    # Responder con la verdad persistida, nunca con el estado optimista del navegador.
                    documentacion = consultar_documentacion(self.object)
                    estado, clase = estado_de_control(
                        control, secciones_exigibles=documentacion.secciones_exigibles)
                    por_seccion = {
                        codigo: {
                            "completos": sum(c.completo for c in documentacion.controles
                                              if c.definicion.seccion == codigo),
                            "total": sum(c.definicion.seccion == codigo for c in documentacion.controles),
                        }
                        for codigo, _ in SECCIONES
                    }
                    return JsonResponse({
                        "ok": True, "version": control.version,
                        "verificado": control.verificado, "fojas": control.fojas,
                        "partida_principal": control.partida_principal,
                        "actividad_presupuestaria": control.actividad_presupuestaria,
                        "observaciones": control.observaciones,
                        "estado": estado, "estado_clase": clase,
                        "completo": control.completo,
                        "usuario": request.user.get_username(),
                        "actualizado_en": timezone.localtime(control.actualizado_en).strftime("%d/%m/%Y %H:%M"),
                        "historial_url": reverse("concursos:control_historial", args=[self.object.pk, control.pk]),
                        "etapa_documental": {
                            "codigo": documentacion.seguimiento.etapa,
                            "nombre": documentacion.seguimiento.get_etapa_display(),
                            "version": documentacion.seguimiento.version,
                        },
                        "estados_controles": {
                            str(item.pk): {
                                "estado": estado_de_control(item, secciones_exigibles=documentacion.secciones_exigibles)[0],
                                "clase": estado_de_control(item, secciones_exigibles=documentacion.secciones_exigibles)[1],
                            }
                            for item in documentacion.controles
                        },
                        "habilitacion_html": render_to_string("expedientes/habilitacion_resumen.html",
                                                           {"documentacion": documentacion}, request=request),
                        "sugerencia_html": render_to_string("expedientes/sugerencia_estado.html", {
                            "documentacion": documentacion, "concurso": self.object,
                        }, request=request),
                        "sugerencia": (
                            {
                                "requisito": documentacion.detalle_sugerencia.requisito,
                                "estado": documentacion.detalle_sugerencia.nombre_estado,
                                "url": (reverse("concursos:estado", args=[self.object.pk]) +
                                        "?sugerencia=" + documentacion.detalle_sugerencia.requisito)
                                       if request.user.has_perm("concursos.cambiar_estado_concurso") else None,
                            }
                            if documentacion.detalle_sugerencia else None
                        ),
                        "totales": {
                            "completos": len(documentacion.completos), "total": documentacion.total,
                            "pendientes": len(documentacion.pendientes_exigibles),
                            "futuros": len(documentacion.no_registrados_futuros),
                            "secciones": por_seccion,
                        },
                    })
                messages.success(request, "El control documental se guardó correctamente.")
                return redirect(f"{self.object.get_absolute_url()}#documental-{control.pk}")
        if auto:
            errores = {campo: [str(mensaje) for mensaje in mensajes]
                       for campo, mensajes in form.errors.items()}
            conflicto = any("Otro operador modificó" in texto
                            for mensajes in errores.values() for texto in mensajes)
            return JsonResponse({"ok": False, "errores": errores}, status=409 if conflicto else 400)
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
