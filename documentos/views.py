from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse, Http404
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import hashlib
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView, View
from concursos.models import Concurso
from concursos.views import AccesoConcursoMixin
from . import services
from .forms import DestinatarioForm, DestinatarioPersonalForm, MembreteInstitucionalForm, GeneracionForm, GRUPOS_CONVOCATORIA
from .models import DestinatarioAPUNSJ, DestinatarioPersonal, MembreteInstitucional, GeneracionDocumento
from .registry import POR_CODIGO


class ConfiguracionView(AccesoConcursoMixin, TemplateView):
    """Portada institucional: las tres configuraciones tienen igual jerarquía."""
    permission_required = "documentos.configurar_institucion"
    template_name = "documentos/configuracion.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            apunsj_actual=DestinatarioAPUNSJ.objects.filter(pk=1).first(),
            personal_actual=DestinatarioPersonal.objects.filter(pk=1).first(),
            membrete_actual=MembreteInstitucional.objects.filter(pk=1).first(),
        )
        return contexto


class ConfiguracionAPUNSJView(AccesoConcursoMixin, FormView):
    """Formulario APUNSJ separado, con permisos y control de versión originales."""
    permission_required = "documentos.configurar_institucion"
    template_name = "documentos/configuracion_apunsj.html"
    form_class = DestinatarioForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = DestinatarioAPUNSJ.objects.filter(pk=1).first()
        return kwargs

    def form_valid(self, form):
        try:
            services.guardar_destinatario(datos=form.cleaned_data, usuario=self.request.user,
                                         version_esperada=form.cleaned_data["version_esperada"])
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "El destinatario de APUNSJ se actualizó. Las generaciones anteriores no se modificaron.")
        return redirect("documentos:configuracion_apunsj")


class DestinatarioPersonalView(AccesoConcursoMixin, FormView):
    permission_required = "documentos.configurar_institucion"
    template_name = "documentos/configuracion_personal.html"
    form_class = DestinatarioPersonalForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = DestinatarioPersonal.objects.filter(pk=1).first()
        return kwargs

    def form_valid(self, form):
        try:
            services.guardar_destinatario_personal(
                datos=form.cleaned_data, usuario=self.request.user,
                version_esperada=form.cleaned_data["version_esperada"])
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Jefatura de Personal actualizada. Los oficios anteriores conservan su destinatario.")
        return redirect("documentos:configuracion_personal")


class MembreteInstitucionalView(AccesoConcursoMixin, FormView):
    permission_required = "documentos.configurar_institucion"
    template_name = "documentos/membrete.html"
    form_class = MembreteInstitucionalForm

    def get_initial(self):
        actual = MembreteInstitucional.objects.filter(pk=1).first()
        return {"version_esperada": actual.version if actual else 0}

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            membrete_actual=MembreteInstitucional.objects.filter(pk=1).first(), **kwargs)

    def form_valid(self, form):
        try:
            services.guardar_membrete(imagen=form.cleaned_data["imagen"], usuario=self.request.user,
                                       version_esperada=form.cleaned_data["version_esperada"])
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Membrete actualizado. Los documentos anteriores conservan su imagen original.")
        return redirect("documentos:membrete")


class ImagenMembreteView(AccesoConcursoMixin, View):
    permission_required = "documentos.configurar_institucion"
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        actual = get_object_or_404(MembreteInstitucional, pk=1)
        response = HttpResponse(bytes(actual.contenido), content_type=actual.tipo_mime)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class GeneracionView(AccesoConcursoMixin, FormView):
    permission_required = services.PERMISOS_GENERACION
    template_name = "documentos/revision.html"
    form_class = GeneracionForm

    def get_concurso(self):
        if not hasattr(self, "concurso"):
            self.concurso = get_object_or_404(Concurso, pk=self.kwargs["pk"])
        return self.concurso

    def get_tipo(self):
        from django.http import Http404
        tipo = POR_CODIGO.get(self.kwargs["tipo"])
        if tipo is None:
            raise Http404
        return tipo

    def get_destinatario(self):
        return DestinatarioAPUNSJ.objects.filter(pk=1).first() if self.get_tipo().codigo == "apunsj" else None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(acotado=self.get_concurso().modalidad == "acotado" and self.get_tipo().codigo != "apunsj",
                      tipo=self.get_tipo(), concurso=self.get_concurso())
        return kwargs

    def get_initial(self):
        destinatario = self.get_destinatario()
        snapshot, _, _, _ = services.fuentes_actuales(self.get_concurso(), self.get_tipo())
        return {"huella_esperada": services.huella_fuentes(snapshot), "version_concurso": self.get_concurso().version,
                "version_destinatario": destinatario.version if destinatario else 0}

    def get_context_data(self, **kwargs):
        concurso = self.get_concurso()
        destinatario = self.get_destinatario()
        snapshot, _, _, _ = services.fuentes_actuales(concurso, self.get_tipo())
        contexto = super().get_context_data(
            concurso=concurso, destinatario=destinatario, fuentes=snapshot,
            datos_concurso=services.instantanea_concurso(concurso)["datos_presentados"],
            disponibilidad=services.disponibilidad(concurso, self.get_tipo(), destinatario), **kwargs)
        form = contexto["form"]
        if self.get_tipo().codigo == "convocatoria":
            contexto["grupos_convocatoria"] = [
                {"codigo": codigo, "titulo": titulo, "descripcion": descripcion,
                 "campos": [form[nombre] for nombre in nombres]}
                for codigo, titulo, descripcion, nombres in GRUPOS_CONVOCATORIA
            ]
        else:
            # Solo agrupar los BoundField existentes: sin nuevas reglas de formulario.
            visibles = list(form.visible_fields())
            contexto["campos_complementarios"] = [campo for campo in visibles
                if not campo.name.startswith("presupuesto_") and campo.name != "revision_administrativa"]
            contexto["campos_presupuesto"] = [campo for campo in visibles if campo.name.startswith("presupuesto_")]
            contexto["errores_presupuesto"] = any(campo.errors for campo in contexto["campos_presupuesto"])
            contexto["campo_revision_administrativa"] = next(
                (campo for campo in visibles if campo.name == "revision_administrativa"), None)
        return contexto

    def form_valid(self, form):
        try:
            datos = dict(form.cleaned_data)
            versiones = {k: datos.pop(k) for k in ("version_concurso", "version_destinatario", "revision_administrativa", "huella_esperada")}
            datos = {campo: self.request.POST.get(campo, "") for campo in form.fields if campo not in versiones}
            generacion = services.generar(complementarios=datos, concurso_id=self.get_concurso().pk, tipo_codigo=self.get_tipo().codigo,
                                          usuario=self.request.user, **versiones)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Borrador generado y conservado sin modificar el expediente ni el estado del concurso.")
        return redirect("documentos:descargar", pk=generacion.concurso_id, documento_id=generacion.pk)


class DescargaView(AccesoConcursoMixin, View):
    permission_required = services.PERMISOS_GENERACION
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk, documento_id, indice=None):
        registro = get_object_or_404(GeneracionDocumento, pk=documento_id, concurso_id=pk)
        contenido = bytes(registro.contenido)
        es_zip = registro.tipo == "jurados"
        extension = "zip" if es_zip else "docx"
        if hashlib.sha256(contenido).hexdigest() != registro.sha256:
            raise Http404("El archivo histórico no superó el control de integridad.")
        if indice is not None:
            miembros = [a for a in registro.instantanea.get("archivos", []) if a["indice"] == indice]
            if not es_zip or len(miembros) != 1:
                raise Http404
            miembro = miembros[0]
            try:
                with ZipFile(BytesIO(contenido)) as archivo:
                    contenido = archivo.read(miembro["nombre"])
            except (BadZipFile, KeyError):
                raise Http404("Archivo histórico no disponible.")
            if hashlib.sha256(contenido).hexdigest() != miembro["sha256"]:
                raise Http404("Archivo histórico no disponible.")
            extension = "docx"
        response = HttpResponse(contenido, content_type="application/zip" if es_zip and indice is None else
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        sufijo = f"-jurado-{indice}" if indice is not None else ""
        response["Content-Disposition"] = f'attachment; filename="concurso-{pk}-documento-{registro.pk}{sufijo}.{extension}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
