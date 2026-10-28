from django import forms
from django.core.exceptions import ValidationError
from core.fields import IdentificadorField, TelefonoField

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
    telefono = TelefonoField()


class VeedorAltaForm(PersonaDatosForm):
    cargo = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(label="Correo electrónico", required=False)
    telefono = TelefonoField()


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
    telefono = TelefonoField()

    class Meta:
        model = Jurado
        fields = ("representacion", "calidad", "titulo", "unidad", "email", "telefono")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["telefono"].conservar_actual(self.instance.telefono)


class VeedorEdicionForm(FormularioVersionado):
    telefono = TelefonoField()

    class Meta:
        model = Veedor
        fields = ("cargo", "email", "telefono")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["telefono"].conservar_actual(self.instance.telefono)


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


class EvaluacionAspiranteForm(forms.Form):
    from .evaluaciones import MAX_ANTECEDENTES, MAX_OPOSICION
    antecedentes = forms.DecimalField(label="Puntaje de antecedentes (sobre 34)", min_value=0,
        max_value=MAX_ANTECEDENTES, decimal_places=2, max_digits=5,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}))
    oposicion = forms.DecimalField(label="Puntaje de oposición (sobre 51)", min_value=0,
        max_value=MAX_OPOSICION, decimal_places=2, max_digits=5,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}))
    version_esperada = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    motivo = forms.CharField(label="Motivo de corrección", required=False, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Obligatorio si se modifica un puntaje registrado anteriormente.")

    def __init__(self, *args, evaluacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.evaluacion = evaluacion
        self.initial["version_esperada"] = evaluacion.version if evaluacion else 0
        if evaluacion:
            self.initial["antecedentes"] = evaluacion.antecedentes
            self.initial["oposicion"] = evaluacion.oposicion

    def clean(self):
        datos = super().clean()
        anterior = self.evaluacion
        if anterior and all(campo in datos for campo in ("antecedentes", "oposicion")):
            modificada = (anterior.antecedentes, anterior.oposicion) != (datos["antecedentes"], datos["oposicion"])
            if modificada and not datos.get("motivo", "").strip():
                self.add_error("motivo", "Indicá el motivo de la corrección de los puntajes.")
        return datos
