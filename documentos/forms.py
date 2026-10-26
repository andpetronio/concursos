from django import forms
from django.core.exceptions import ValidationError
from docx.image.image import Image as ImagenDocx
from .models import DestinatarioAPUNSJ, DestinatarioPersonal


class DestinatarioForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = DestinatarioAPUNSJ
        fields = ("tratamiento", "cargo", "titulo", "nombre", "apellido")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("tratamiento", "cargo"):
            self.fields[campo].choices = [("", "Seleccioná una opción"), *self.fields[campo].choices[1:]]
        self.fields["version_esperada"].initial = self.instance.version if self.instance.pk else 0


class DestinatarioPersonalForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = DestinatarioPersonal
        fields = ("tratamiento", "cargo", "titulo", "nombre", "apellido")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("tratamiento", "cargo"):
            self.fields[campo].choices = [("", "Seleccioná una opción"), *self.fields[campo].choices[1:]]
        self.fields["version_esperada"].initial = self.instance.version if self.instance.pk else 0


class MembreteInstitucionalForm(forms.Form):
    imagen = forms.FileField(
        label="Imagen del membrete vigente",
        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg"}),
        help_text="Subí el membrete institucional completo en PNG o JPG (máximo 4 MB). Incluí los logos vigentes del año.",
    )
    version_esperada = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    def clean_imagen(self):
        archivo = self.cleaned_data["imagen"]
        if archivo.size > 4 * 1024 * 1024:
            raise ValidationError("La imagen supera el máximo de 4 MB.")
        blob = archivo.read(4 * 1024 * 1024 + 1)
        if len(blob) > 4 * 1024 * 1024:
            raise ValidationError("La imagen supera el máximo de 4 MB.")
        try:
            imagen = ImagenDocx.from_blob(blob)
        except Exception as error:
            raise ValidationError("La imagen no es un PNG o JPG válido.") from error
        if imagen.content_type not in ("image/png", "image/jpeg"):
            raise ValidationError("Solo se permiten imágenes PNG o JPG.")
        if imagen.px_width < 300 or imagen.px_height < 60 or imagen.px_width * imagen.px_height > 16_000_000:
            raise ValidationError("La imagen debe tener al menos 300 × 60 píxeles y no superar 16 megapíxeles.")
        return {"contenido": blob, "tipo_mime": imagen.content_type, "nombre_archivo": archivo.name[:150]}


class GeneracionForm(forms.Form):
    huella_esperada = forms.CharField(min_length=64, max_length=64, widget=forms.HiddenInput)
    version_concurso = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    version_destinatario = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    revision_administrativa = forms.BooleanField(
        required=False, label="Revisé administrativamente el uso de este borrador para la modalidad Acotado.")

    def __init__(self, *args, acotado=False, tipo=None, concurso=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["revision_administrativa"].required = acotado
        if not acotado:
            self.fields["revision_administrativa"].widget = forms.HiddenInput()

        self.tipo = tipo
        self.concurso = concurso
        if tipo and tipo.codigo == "convocatoria":
            self.fields["fecha_apertura"] = forms.DateField(
                label="Fecha de apertura de inscripciones", input_formats=["%Y-%m-%d"],
                widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                help_text="Desde esta fecha, durante cinco (5) días hábiles, siempre de 8 a 12 hs.")
        if tipo and tipo.codigo not in ("apunsj", "elecciones"):
            if tipo.codigo != "convocatoria":
                for nombre, etiqueta, tipos, largo in COMPLEMENTOS:
                    if tipo.codigo in tipos and not (tipo.codigo == "jurados" and nombre in ("marco_normativo", "firmante", "lugar_fecha")):
                        self.fields[nombre] = forms.CharField(label=etiqueta, required=True, max_length=largo,
                            widget=forms.Textarea(attrs={"rows": 3}) if largo > 300 else forms.TextInput(),
                            help_text="Ingresá el texto completo acreditado para este concurso; no se presume ningún hecho del modelo.")
            if tipo.codigo in POSTERIORES:
                opciones = list(concurso.aspirantes.select_related("persona").all())
                self.fields["merito"].help_text = "Una línea por puesto: puesto | ID de aspirante. IDs: " + "; ".join(
                    f"{a.pk}: {a.persona.apellido}, {a.persona.nombre}" for a in opciones)
            if tipo.codigo == "designacion":
                for nombre, etiqueta in PRESUPUESTO:
                    self.fields[f"presupuesto_{nombre}"] = forms.CharField(label=etiqueta, max_length=200,
                        help_text="" if tipo.codigo == "convocatoria" else
                        "Valor de la afectación presupuestaria acreditada, sin valores predeterminados.")
            if tipo.codigo == "designacion":
                self.fields["aplica_limitacion"] = forms.TypedChoiceField(
                    label="¿Corresponde limitar una designación anterior?", coerce=lambda valor: valor == "si",
                    choices=[("", "Seleccioná expresamente"), ("si", "Sí, con texto completo acreditado"), ("no", "No corresponde")])
                self.fields["limitacion"].required = False
                self.fields["aspirante_id"] = forms.ChoiceField(label="Persona propuesta para designación", required=True,
                    choices=[("", "Seleccioná expresamente una persona")]+[
                        (str(a.pk), f"{a.persona.apellido}, {a.persona.nombre}")
                        for a in concurso.aspirantes.select_related("persona").all()])

    def clean(self):
        datos = super().clean()
        if self.tipo and self.tipo.codigo in POSTERIORES and datos.get("merito"):
            ids = set(self.concurso.aspirantes.values_list("pk", flat=True))
            posiciones, personas, orden = set(), set(), []
            try:
                for linea in datos["merito"].splitlines():
                    puesto, persona_id = (int(valor.strip()) for valor in linea.split("|"))
                    if puesto < 1 or persona_id not in ids or puesto in posiciones or persona_id in personas:
                        raise ValueError
                    posiciones.add(puesto)
                    personas.add(persona_id)
                    orden.append({"puesto": puesto, "aspirante_id": persona_id})
                if posiciones != set(range(1, len(orden) + 1)):
                    raise ValueError
            except (ValueError, TypeError):
                self.add_error("merito", "Indicá puestos consecutivos desde 1, sin duplicados, con IDs de aspirantes de este concurso: puesto | ID.")
            else:
                datos["orden_merito"] = sorted(orden, key=lambda fila: fila["puesto"])
        if datos.get("aplica_limitacion") and not datos.get("limitacion"):
            self.add_error("limitacion", "El texto completo acreditado es obligatorio cuando corresponde limitar una designación.")
        return datos


# Un único catálogo de complementos, compartido por revisión y validación del servicio.
TODOS = ("convocatoria", "jurados", "dictamen", "designacion", "elecciones")
RESOLUCIONES = ("convocatoria", "dictamen", "designacion")
POSTERIORES = ("dictamen", "designacion")
COMPLEMENTOS = (
    ("marco_normativo", "Fundamento normativo revisado para esta modalidad y este documento (denominaciones exactas)", TODOS, 3000),
    ("procedimiento_eleccion", "Procedimiento acreditado de elección, condiciones de electores/candidatos y fiscalización", ("elecciones",), 3000),
    ("lugar_fecha", "Lugar y fecha del borrador (no de emisión)", TODOS, 200),
    ("firmante", "Autoridad firmante propuesta y cargo", TODOS, 300),
    ("autoridad_resuelve", "Autoridad competente que resolvería (denominación completa)", RESOLUCIONES, 300),
    ("res_convocatoria", "Número y fecha de resolución oficial de convocatoria (si consta)", ("dictamen", "designacion"), 200),
    ("antecedentes_inscriptos", "Acta de inscriptos: autoridades suscribientes y circunstancias acreditadas", POSTERIORES, 1500),
    ("valoracion", "Valoración de antecedentes y programación de sorteo y oposición acreditadas", POSTERIORES, 2000),
    ("sorteo", "Sorteo: fecha, hora, asistentes y comunicación del tema acreditados", POSTERIORES, 2000),
    ("prueba", "Prueba de oposición: fecha, hora, realización y elaboración del examen acreditadas", POSTERIORES, 2000),
    ("resultado", "Dictamen: resultados de evaluación, decisiones y votos acreditados", POSTERIORES, 3000),
    ("impugnaciones", "Impugnaciones, observaciones y recursos: situación acreditada", POSTERIORES, 2000),
    ("comunicacion", "Comunicación del dictamen: fechas, destinatarios y constancias acreditadas", POSTERIORES, 2000),
    ("tramites", "Cumplimiento de trámites formales acreditado", POSTERIORES, 2000),
    ("merito", "Orden de mérito acreditado (un puesto y persona por línea; nunca se deduce de inscripciones)", POSTERIORES, 3000),
    ("res_dictamen", "Resolución oficial de aprobación del dictamen: número y fecha", ("designacion",), 200),
    ("efectos", "Fecha o condición acreditada de efectos de la designación", ("designacion",), 500),
    ("limitacion", "Texto completo acreditado de limitación anterior (solo si corresponde)", ("designacion",), 2500),
    ("circuito", "Circuito de notificación y actuaciones posteriores aplicable a la unidad", ("designacion",), 1500),
    ("destinatario_nota", "Tratamiento, nombre y cargo del destinatario", ("elecciones",), 300),
)

PRESUPUESTO = (
    ("unidad", "Unidad presupuestaria"), ("unidad_cargo", "Unidad donde se ubica el cargo"),
    ("ejercicio", "Ejercicio financiero"), ("grupo", "Grupo presupuestario"),
    ("ppal", "Unidad principal"), ("subppal", "Subprincipal"), ("subsubppal", "Subsubprincipal"),
    ("fte", "Fuente"), ("prog", "Programa"), ("sprog", "Subprograma"), ("proy", "Proyecto"),
    ("activ", "Actividad"), ("obra", "Obra"), ("finalidad", "Finalidad"), ("funcion", "Función presupuestaria"),
    ("planta", "Planta"), ("inciso", "Inciso"), ("partida", "Partida principal"),
    ("caracter", "Carácter de designación"), ("escalafon", "Escalafón"), ("numero_cargo", "Número de cargo"),
)

# Presentación únicamente: mismos campos complementarios y validaciones de SDD-005.
# No se crean datos duplicados ni se mezclan con la ficha maestra del concurso.
GRUPOS_CONVOCATORIA = (
    ("inscripciones", "Inscripciones",
     "El resto del texto se completa desde la plantilla, el concurso y el expediente.",
     ("fecha_apertura",)),
)
