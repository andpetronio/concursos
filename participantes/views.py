from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from concursos.models import Concurso
from concursos.views import AccesoConcursoMixin

from . import services
from .forms import (AspiranteAltaForm, JuradoAltaForm, JuradoEdicionForm,
                    PersonaEdicionForm, VeedorAltaForm, VeedorEdicionForm)
from .models import Aspirante, Jurado, Persona, Veedor


class ParticipanteFormView(AccesoConcursoMixin, FormView):
    template_name = "participantes/formulario.html"
    titulo = ""
    descripcion = ""
    boton = "Guardar"

    def get_concurso(self):
        if not hasattr(self, "concurso"):
            self.concurso = get_object_or_404(Concurso, pk=self.kwargs["pk"])
        return self.concurso

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            concurso=self.get_concurso(), title=self.titulo,
            description=self.descripcion, button_label=self.boton, **kwargs,
        )

    def get_success_url(self):
        return reverse("concursos:detalle", args=[self.get_concurso().pk])


class AltaParticipanteView(ParticipanteFormView):
    permission_required = ("concursos.view_concurso", "concursos.add_concurso")
    modelo = None

    def form_valid(self, form):
        try:
            services.crear_participacion(
                modelo=self.modelo, concurso=self.get_concurso(), datos=form.cleaned_data,
                usuario=self.request.user, persona_id=getattr(form, "persona_id", None),
            )
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, error if isinstance(error, ValidationError)
                           else "Ya existe una participación para esta persona o plaza en el concurso.")
            return self.form_invalid(form)
        messages.success(self.request, "La participación se registró correctamente.")
        return redirect(self.get_success_url())


class JuradoAltaView(AltaParticipanteView):
    modelo = Jurado
    form_class = JuradoAltaForm
    titulo = "Agregar integrante del jurado"
    descripcion = "Elegí una representación y calidad. Podés completar el jurado progresivamente."
    boton = "Agregar al jurado"


class VeedorAltaView(AltaParticipanteView):
    modelo = Veedor
    form_class = VeedorAltaForm
    titulo = "Agregar veedor de APUNSJ"
    descripcion = "La representación es siempre APUNSJ. Su ausencia no bloquea el concurso."
    boton = "Agregar veedor"


class AspiranteAltaView(AltaParticipanteView):
    modelo = Aspirante
    form_class = AspiranteAltaForm
    titulo = "Agregar aspirante"
    descripcion = "Cargá los datos del acta de inscriptos recibida, sin crear dependencias automáticas con el checklist."
    boton = "Agregar aspirante"


class EdicionParticipanteView(ParticipanteFormView):
    permission_required = ("concursos.view_concurso", "concursos.change_concurso")
    modelo = None

    def get_participacion(self):
        if not hasattr(self, "participacion"):
            self.participacion = get_object_or_404(
                self.modelo, pk=self.kwargs["participacion_id"], concurso=self.get_concurso()
            )
        return self.participacion

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_participacion()
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            identity=self.get_participacion().persona,
            **kwargs,
        )

    def form_valid(self, form):
        try:
            services.editar_participacion(
                participacion=self.get_participacion(),
                datos={campo: valor for campo, valor in form.cleaned_data.items() if campo != "version_esperada"},
                usuario=self.request.user, version_esperada=form.cleaned_data["version_esperada"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Los datos de la participación se actualizaron correctamente.")
        return redirect(self.get_success_url())


class JuradoEdicionView(EdicionParticipanteView):
    modelo = Jurado
    form_class = JuradoEdicionForm
    titulo = "Editar datos del jurado"
    descripcion = "Estos datos corresponden a la participación en este concurso."
    boton = "Guardar datos del jurado"


class VeedorEdicionView(EdicionParticipanteView):
    modelo = Veedor
    form_class = VeedorEdicionForm
    titulo = "Editar datos del veedor"
    descripcion = "Estos datos corresponden a la participación de APUNSJ en este concurso."
    boton = "Guardar datos del veedor"


class PersonaEdicionView(ParticipanteFormView):
    permission_required = ("concursos.view_concurso", "concursos.change_concurso")
    form_class = PersonaEdicionForm
    titulo = "Corregir datos personales"
    descripcion = "Los cambios de nombre y apellido se reflejan en todos los concursos de esta persona."
    boton = "Guardar datos personales"

    def get_persona(self):
        if not hasattr(self, "persona"):
            persona = get_object_or_404(Persona, pk=self.kwargs["persona_id"])
            if not any(model.objects.filter(concurso=self.get_concurso(), persona=persona).exists()
                       for model in (Jurado, Veedor, Aspirante)):
                from django.http import Http404
                raise Http404
            self.persona = persona
        return self.persona

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_persona()
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(identity=self.get_persona(), **kwargs)

    def form_valid(self, form):
        try:
            services.editar_persona(
                persona=self.get_persona(),
                datos={campo: valor for campo, valor in form.cleaned_data.items() if campo != "version_esperada"},
                usuario=self.request.user, version_esperada=form.cleaned_data["version_esperada"],
            )
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, error if isinstance(error, ValidationError)
                           else "El DNI ya está registrado para otra persona.")
            return self.form_invalid(form)
        messages.success(self.request, "Los datos personales se actualizaron correctamente.")
        return redirect(self.get_success_url())
