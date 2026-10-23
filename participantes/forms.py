from django import forms
from django.core.exceptions import ValidationError
from core.fields import IdentificadorField, TelefonoInput

from .models import Aspirante, Jurado, Persona, Veedor


class PersonaDatosForm(forms.Form):
    apellido = forms.CharField(max_length=100)
    nombre = forms.CharField(max_length=100)
    dni = IdentificadorField(formato="dni", max_length=20)

    def clean(self):
        datos = super().clean()
        if all(datos.get(campo) for campo in ("apellido", "nombre", "dni")):
            persona = Persona.objects.filter(dni=datos["dni"]).first()
            if persona and (persona.apellido.casefold() != datos["apellido"].casefold()
                            or persona.nombre.casefold() != datos["nombre"].casefold()):
                raise ValidationError(
                    "Este DNI ya está registrado con otro nombre o apellido. No se modificaron los datos compartidos; revisá la identidad antes de vincularla."
                )
            self.persona_id = persona.pk if persona else None
        return datos


class JuradoAltaForm(PersonaDatosForm):
    representacion = forms.ChoiceField(
        label="Representación", choices=[("", "Seleccioná una representación"), *Jurado.Representacion.choices],
    )
    calidad = forms.ChoiceField(label="Calidad", choices=[("", "Seleccioná una calidad"), *Jurado.Calidad.choices])
    titulo = forms.CharField(label="Título", max_length=150)
    unidad = Jurado._meta.get_field("unidad").formfield()
    email = forms.EmailField(label="Correo electrónico", required=False)
    telefono = forms.CharField(label="Teléfono", max_length=40, required=False, widget=TelefonoInput)


class VeedorAltaForm(PersonaDatosForm):
    cargo = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(label="Correo electrónico", required=False)
    telefono = forms.CharField(label="Teléfono", max_length=40, required=False, widget=TelefonoInput)


class AspiranteAltaForm(PersonaDatosForm):
    email = forms.EmailField(label="Correo electrónico", max_length=254, required=False)
    expediente_inscripcion = IdentificadorField(
        formato="expediente", label="Expediente de inscripción", max_length=100, required=False,
    )


class FormularioVersionado(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["version_esperada"] = self.instance.version


class JuradoEdicionForm(FormularioVersionado):
    class Meta:
        model = Jurado
        fields = ("representacion", "calidad", "titulo", "unidad", "email", "telefono")
        widgets = {"telefono": TelefonoInput}


class VeedorEdicionForm(FormularioVersionado):
    class Meta:
        model = Veedor
        fields = ("cargo", "email", "telefono")
        widgets = {"telefono": TelefonoInput}


class AspiranteEdicionForm(FormularioVersionado):
    expediente_inscripcion = IdentificadorField(
        formato="expediente", label="Expediente de inscripción", max_length=100, required=False,
    )

    class Meta:
        model = Aspirante
        fields = ("email", "expediente_inscripcion")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["expediente_inscripcion"].conservar_actual(self.instance.expediente_inscripcion)


class PersonaEdicionForm(FormularioVersionado):
    dni = IdentificadorField(formato="dni", max_length=20)

    class Meta:
        model = Persona
        fields = ("apellido", "nombre", "dni")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["dni"].conservar_actual(self.instance.dni)

    def clean(self):
        datos = super().clean()
        if "dni" in datos and self.instance.pk and datos["dni"] != self.instance.dni:
            concursos = set()
            for model in (Jurado, Veedor, Aspirante):
                concursos.update(model.objects.filter(persona=self.instance).values_list("concurso_id", flat=True))
            if len(concursos) > 1:
                self.add_error("dni", "No se puede cambiar el DNI de una persona vinculada a varios concursos. Solicitá una revisión administrativa.")
        return datos
