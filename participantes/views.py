from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from concursos.models import Concurso
from concursos.views import AccesoConcursoMixin

from . import services
from .forms import (AspiranteAltaForm, AspiranteEdicionForm, JuradoAltaForm, JuradoEdicionForm,
                    PersonaEdicionForm, VeedorAltaForm, VeedorEdicionForm, EvaluacionAspiranteForm)
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
        section = {Jurado: "jurados", Veedor: "veedores", Aspirante: "aspirantes"}.get(
            getattr(self, "modelo", None), "resumen"
        )
        return f'{reverse("concursos:detalle", args=[self.get_concurso().pk])}#{section}'


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


class AspiranteEdicionView(EdicionParticipanteView):
    modelo = Aspirante
    form_class = AspiranteEdicionForm
    titulo = "Editar inscripción del aspirante"
    descripcion = "El correo y el expediente corresponden a esta inscripción. Ambos son opcionales."
    boton = "Guardar inscripción"


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

    def get_success_url(self):
        # Only known sections where this person participates; never a redirect URL.
        section = self.request.GET.get("seccion")
        model = {"jurados": Jurado, "veedores": Veedor, "aspirantes": Aspirante}.get(section)
        if model and model.objects.filter(concurso=self.get_concurso(), persona=self.get_persona()).exists():
            return f'{reverse("concursos:detalle", args=[self.get_concurso().pk])}#{section}'
        return super().get_success_url()

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


class EvaluacionAspiranteView(ParticipanteFormView):
    permission_required = ("concursos.view_concurso", "concursos.change_concurso")
    form_class = EvaluacionAspiranteForm
    template_name = "participantes/evaluacion.html"
    titulo = "Evaluación del aspirante"
    descripcion = "Registrá los puntajes acreditados por el jurado. El total y el mérito se calculan automáticamente."
    boton = "Guardar evaluación"

    def get_aspirante(self):
        if not hasattr(self, "aspirante"):
            self.aspirante = get_object_or_404(
                Aspirante.objects.select_related("persona"), pk=self.kwargs["participacion_id"],
                concurso=self.get_concurso())
        return self.aspirante

    def get_evaluacion(self):
        from .models import EvaluacionAspirante
        return EvaluacionAspirante.objects.filter(aspirante=self.get_aspirante()).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["evaluacion"] = self.get_evaluacion()
        return kwargs

    def get_context_data(self, **kwargs):
        from .evaluaciones import MAX_ANTECEDENTES, MAX_OPOSICION, MINIMO_MERITO
        return super().get_context_data(
            identity=self.get_aspirante().persona,
            max_antecedentes=MAX_ANTECEDENTES, max_oposicion=MAX_OPOSICION,
            minimo_merito=MINIMO_MERITO, cambios=self.get_evaluacion().cambios.select_related("usuario")[:10]
                if self.get_evaluacion() else [],
            **kwargs)

    def get_success_url(self):
        return f'{reverse("concursos:detalle", args=[self.get_concurso().pk])}#aspirantes'

    def form_valid(self, form):
        try:
            services.guardar_evaluacion(
                aspirante=self.get_aspirante(), antecedentes=form.cleaned_data["antecedentes"],
                oposicion=form.cleaned_data["oposicion"], usuario=self.request.user,
                version_esperada=form.cleaned_data["version_esperada"],
                motivo=form.cleaned_data.get("motivo", ""))
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "La evaluación se registró. El orden de mérito se actualiza a partir de los puntajes.")
        return redirect(self.get_success_url())
