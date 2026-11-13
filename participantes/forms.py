from django import forms
from django.core.exceptions import ValidationError
from core.fields import IdentificadorField, TelefonoField

from .models import Aspirante, CambioSituacionAspirante, Jurado, Persona, Veedor


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
        fields = ("titulo", "unidad", "email", "telefono")

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
        max_value=MAX_ANTECEDENTES, decimal_places=2, max_digits=5, required=False,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}))
    oposicion = forms.DecimalField(label="Puntaje de oposición (sobre 51)", min_value=0,
        max_value=MAX_OPOSICION, decimal_places=2, max_digits=5, required=False,
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
            # Completar un puntaje que estaba pendiente no es una corrección.
            rectifica = any(
                getattr(anterior, campo) is not None
                and getattr(anterior, campo) != datos[campo]
                for campo in ("antecedentes", "oposicion")
            )
            if rectifica and not datos.get("motivo", "").strip():
                self.add_error("motivo", "Indicá el motivo de la corrección de los puntajes.")
        return datos


class ActuacionAspiranteForm(forms.Form):

    tipo = forms.ChoiceField(label="Situación o actuación acreditada", choices=[("", "Seleccioná una actuación")] +
                             list(CambioSituacionAspirante.Tipo.choices),
                             help_text="Al cambiar de actuación se limpian los datos cargados para evitar mezclar respaldos.")
    motivo_exclusion = forms.ChoiceField(
        label="Motivo de exclusión", required=False,
        choices=[
            (Aspirante.MotivoExclusion.REQUISITOS, "Por no cumplir los requisitos · Jurado · acta"),
            (Aspirante.MotivoExclusion.IMPUGNACION_ACEPTADA, "Por aceptación de impugnación · Rector · resolución"),
        ], widget=forms.RadioSelect,
        help_text=("Solo para Excluido. Por requisitos: decisión del Jurado respaldada en acta. "
                   "Por impugnación aceptada: decisión del Rector respaldada en resolución rectoral."))
    fecha_decision = forms.DateField(label="Fecha de la actuación", widget=forms.DateInput(
        attrs={"type": "date"}, format="%Y-%m-%d"), input_formats=["%Y-%m-%d"])
    clase_documento = forms.ChoiceField(label="Tipo de respaldo", choices=[("", "Seleccioná")]+
        list(CambioSituacionAspirante.Documento.choices),
        help_text="Seleccioná el documento que respalda esta actuación. En caso de exclusión, se establece según el motivo.")
    documento = forms.CharField(label="Identificación del documento respaldatorio", max_length=250)
    fojas = forms.CharField(label="Fojas del expediente", max_length=50,
        help_text="Indicá la foja o rango donde consta la actuación. Ejemplo: 125/127.")
    fundamento = forms.CharField(label="Fundamento consignado en la actuación", max_length=1500,
        widget=forms.Textarea(attrs={"rows": 4}))
    constancia_comunicacion = forms.CharField(label="Constancia de notificación o publicación", required=False,
        max_length=300, help_text="Opcional; registrá únicamente lo que consta efectivamente.")
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    def __init__(self, *args, aspirante, **kwargs):
        super().__init__(*args, **kwargs)
        self.aspirante = aspirante
        # Ofrecer solo transiciones pertinentes a la situación vigente.
        # Una impugnación pendiente puede cerrarse sin excluir a la persona:
        # esa actuación retorna a Inscripto, conservando el historial.
        if aspirante.situacion == Aspirante.Situacion.INSCRIPTO:
            opciones = [
                (CambioSituacionAspirante.Tipo.IMPUGNACION, "Registrar impugnación en trámite"),
                (CambioSituacionAspirante.Tipo.EXCLUSION, "Registrar exclusión"),
                (CambioSituacionAspirante.Tipo.DESISTIMIENTO, "Registrar desistimiento"),
            ]
        elif aspirante.situacion == Aspirante.Situacion.IMPUGNACION_PENDIENTE:
            opciones = [
                (CambioSituacionAspirante.Tipo.RECTIFICACION, "Cerrar impugnación sin exclusión"),
                (CambioSituacionAspirante.Tipo.EXCLUSION, "Registrar exclusión"),
                (CambioSituacionAspirante.Tipo.DESISTIMIENTO, "Registrar desistimiento"),
            ]
            self.fields["clase_documento"].help_text = (
                "Indicá el documento que acredita la resolución o actuación registrada."
            )
        else:
            opciones = [
                (CambioSituacionAspirante.Tipo.RECTIFICACION, "Rectificar o dejar sin efecto la decisión"),
            ]
            self.initial["tipo"] = CambioSituacionAspirante.Tipo.RECTIFICACION
            self.fields["clase_documento"].help_text = (
                "Seleccioná la actuación formal que respalda la rectificación."
            )
            self.fields["motivo_exclusion"].widget = forms.HiddenInput()
        self.fields["tipo"].choices = [("", "Seleccioná una actuación"), *opciones]
        self.initial["version_esperada"] = aspirante.version

    def clean(self):
        from .situaciones import DESTINOS
        datos = super().clean()
        if datos.get("tipo") in DESTINOS:
            if DESTINOS[datos["tipo"]] == self.aspirante.situacion:
                self.add_error("tipo", "Esta actuación no modifica la situación vigente.")
        motivo = datos.get("motivo_exclusion", "")
        if datos.get("tipo") == CambioSituacionAspirante.Tipo.EXCLUSION:
            if not motivo:
                self.add_error("motivo_exclusion", "Seleccioná el motivo de exclusión.")
            elif motivo == Aspirante.MotivoExclusion.REQUISITOS and datos.get("clase_documento") not in (None, "acta"):
                self.add_error("clase_documento", "La exclusión por requisitos requiere el acta del Jurado.")
            elif motivo == Aspirante.MotivoExclusion.IMPUGNACION_ACEPTADA and datos.get("clase_documento") not in (None, "resolucion"):
                self.add_error("clase_documento", "La exclusión por impugnación aceptada requiere una resolución rectoral.")
        elif motivo:
            self.add_error("motivo_exclusion", "Seleccioná un motivo solamente para una exclusión.")
        if datos.get("fojas"):
            from expedientes.validators import normalizar_fojas
            try:
                datos["fojas"] = normalizar_fojas(datos["fojas"])
            except ValidationError as error:
                self.add_error("fojas", error)
        return datos
