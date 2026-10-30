from django import forms
from django.core.exceptions import ValidationError
from docx.image.image import Image as ImagenDocx
from .models import DestinatarioAPUNSJ, DestinatarioPersonal
from core.fields import IdentificadorField
from .temario_rico import leer_temario


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
                    if tipo.codigo in tipos and not (tipo.codigo == "jurados" and nombre in ("marco_normativo", "firmante", "lugar_fecha")) \
                        and not (tipo.codigo in ("dictamen", "designacion") and nombre not in ("res_dictamen", "merito")):
                        self.fields[nombre] = forms.CharField(label=etiqueta, required=True, max_length=largo,
                            widget=forms.Textarea(attrs={"rows": 3}) if largo > 300 else forms.TextInput(),
                            help_text="Ingresá el texto completo acreditado para este concurso; no se presume ningún hecho del modelo.")
            if tipo.codigo == "desierto_inscriptos":
                self.fields["confirmacion_acta_sin_inscriptos"] = forms.BooleanField(
                    required=True,
                    label="Confirmo que el acta de cierre de inscripciones acredita que no se presentaron aspirantes",
                    help_text="Verificá el contenido del acta y las fojas del expediente. No basta con que SiCon tenga cero aspirantes cargados.")
            if tipo.codigo == "dictamen":
                # El orden ordinario surge de evaluaciones estructuradas, no de un textarea libre.
                del self.fields["merito"]
                self.fields["confirmacion_sin_recursos"] = forms.BooleanField(
                    label="Confirmo que no hay recursos contra el dictamen pendientes de resolución",
                    required=True,
                    help_text="Este modelo corresponde a la aprobación ordinaria. No sustituye la verificación del expediente.")
            # Datos estructurados de los modelos DOCX institucionales, nunca inventados.
            if tipo.codigo in ("dictamen", "designacion", "sorteo_acta"):
                for campo, etiqueta in (
                    ("fecha_sorteo_tema", "Fecha del sorteo de temas"),
                    ("fecha_oposicion", "Fecha de la prueba de oposición"),
                ):
                    self.fields[campo] = forms.DateField(label=etiqueta,
                        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
                for campo, etiqueta in (
                    ("hora_sorteo_tema", "Hora del sorteo"),
                    ("hora_oposicion", "Hora de la oposición"),
                ):
                    self.fields[campo] = forms.TimeField(label=etiqueta,
                        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                        input_formats=["%H:%M", "%H:%M:%S"])
                self.fields["autoridad_tratamiento"] = forms.CharField(label="Tratamiento de la autoridad fiscalizadora", max_length=50)
                self.fields["autoridad_cargo"] = forms.CharField(label="Cargo de la autoridad fiscalizadora", max_length=200)
                self.fields["autoridad_nombre"] = forms.CharField(label="Nombre completo y títulos de la autoridad fiscalizadora", max_length=250)
            if tipo.codigo in ("dictamen", "designacion"):
                for nombre, etiqueta in (
                    ("confirmar_suscriptores", "Confirmo que el acta de cierre fue firmada por las autoridades mencionadas en el modelo"),
                    ("confirmar_unanimidad", "Confirmo que el dictamen fue emitido por unanimidad"),
                    ("confirmar_sin_impugnaciones", "Confirmo que no se interpusieron impugnaciones ni observaciones a los antecedentes"),
                    ("confirmar_notificacion", "Confirmo que el dictamen fue notificado en el plazo indicado y no fue recurrido"),
                    ("confirmar_notificacion_sorteo", "Confirmo la presencia y la comunicación del sorteo indicadas en el modelo"),
                ):
                    self.fields[nombre] = forms.BooleanField(required=True, label=etiqueta,
                        help_text="El DOCX reproduce literalmente esta afirmación del modelo; acreditala en el expediente.")
            if tipo.codigo == "sorteo_acta":
                self.fields["jurados_presentes"] = forms.MultipleChoiceField(
                    label="Jurados que asistieron (uno o más)", required=True,
                    choices=[(str(j.pk), f"{j.persona.apellido}, {j.persona.nombre} · {j.get_representacion_display()} · {j.get_calidad_display()}")
                        for j in concurso.jurados.select_related("persona").all()],
                    widget=forms.CheckboxSelectMultiple)
                self.fields["aspirantes_presentes"] = forms.MultipleChoiceField(
                    label="Aspirantes que estuvieron presentes (ninguno o más)", required=False,
                    choices=[(str(a.pk), f"{a.persona.apellido}, {a.persona.nombre} · DNI {a.persona.dni}")
                        for a in concurso.aspirantes.select_related("persona").all() if a.puede_rendir],
                    widget=forms.CheckboxSelectMultiple)
                self.fields["veedor_presencia"] = forms.ChoiceField(
                    label="Participación gremial en el sorteo",
                    choices=[("presente", "Veedor presente"),
                             ("ausente", "Veedor designado, ausente"),
                             ("sin_designacion", "APUNSJ no informó designación de veedor")],
                    widget=forms.RadioSelect)
                self.fields["veedor_id"] = forms.ChoiceField(label="Veedor gremial presente", required=False,
                    choices=[("", "No corresponde / seleccionar")] +
                        [(str(v.pk), f"{v.persona.apellido}, {v.persona.nombre}")
                            for v in concurso.veedors.select_related("persona").all()])
                self.fields["oficio_veedor"] = IdentificadorField(formato="expediente", label="Número de oficio invitando a APUNSJ", required=False, max_length=100)
                self.fields["jurado_autor_tema"] = forms.ChoiceField(label="Jurado autor del temario sorteado",
                    choices=[("", "Seleccioná al autor")] +
                        [(str(j.pk), f"{j.persona.apellido}, {j.persona.nombre}")
                            for j in concurso.jurados.select_related("persona").all()])
                self.fields["tema_teoria"] = forms.CharField(label="Contenido del tema teórico sorteado", max_length=16000,
                    widget=forms.Textarea(attrs={"rows": 5, "data-richtext": "temario"}))
                self.fields["tema_practica"] = forms.CharField(label="Contenido del tema práctico sorteado", max_length=16000,
                    widget=forms.Textarea(attrs={"rows": 5, "data-richtext": "temario"}))
                self.fields["sede_oposicion"] = forms.CharField(label="Sede de la prueba de oposición", max_length=250)
                self.fields["caracter_oposicion"] = forms.CharField(label="Carácter de la prueba de oposición", max_length=100)
                self.fields["hora_cierre"] = forms.TimeField(label="Hora de cierre del acto",
                    widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                    input_formats=["%H:%M", "%H:%M:%S"])
            if tipo.codigo == "designacion":
                for campo, etiqueta in (
                    ("resolucion_anterior", "Resolución de designación anterior a limitar"),
                    ("categoria_anterior", "Categoría del cargo anterior"),
                    ("tramo_anterior", "Tramo del cargo anterior"),
                    ("agrupamiento_anterior", "Agrupamiento y número del cargo anterior"),
                    ("cp_anterior", "Código presupuestario del cargo anterior"),
                    ("funciones_anteriores", "Unidad o funciones del cargo anterior"),
                    ("unidad_anterior", "Dependencias del cargo anterior (cadena completa)"),
                ):
                    self.fields[campo] = forms.CharField(label=etiqueta, max_length=500, required=False,
                        help_text="Obligatorio únicamente si corresponde limitar una designación anterior.")
            if tipo.codigo == "designacion":
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
                self.fields["aspirante_id"] = forms.ChoiceField(label="Persona propuesta para designación", required=True,
                    choices=[("", "Seleccioná expresamente una persona")]+[
                        (str(a.pk), f"{a.persona.apellido}, {a.persona.nombre}")
                        for a in concurso.aspirantes.select_related("persona").all()])

    def clean(self):
        datos = super().clean()
        # CheckboxInput interpreta cualquier cadena no vacía como True, incluso
        # espacios o texto arbitrario. Una afirmación administrativa exige que
        # el operador marque efectivamente la casilla.
        confirmaciones = (
            "confirmacion_acta_sin_inscriptos", "confirmacion_sin_recursos",
            "confirmar_suscriptores", "confirmar_unanimidad",
            "confirmar_sin_impugnaciones", "confirmar_notificacion",
            "confirmar_notificacion_sorteo",
        )
        for nombre in confirmaciones:
            if nombre not in self.fields or nombre in self.errors:
                continue
            valor = self.data.get(self.add_prefix(nombre))
            marcado = valor is True or (type(valor) is int and valor == 1) or (
                isinstance(valor, str) and valor.lower() in ("on", "true", "1"))
            if not marcado:
                self.add_error(nombre, "Marcá la casilla para confirmar expresamente este hecho.")

        if self.tipo and self.tipo.codigo == "designacion" and datos.get("merito"):
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
        if self.tipo and self.tipo.codigo == "designacion" and datos.get("aplica_limitacion"):
            for campo in ("resolucion_anterior", "categoria_anterior", "tramo_anterior",
                          "agrupamiento_anterior", "cp_anterior", "funciones_anteriores", "unidad_anterior"):
                if not datos.get(campo):
                    self.add_error(campo, "Completá este dato de la designación anterior.")
        if self.tipo and self.tipo.codigo == "sorteo_acta":
            for campo in ("tema_teoria", "tema_practica"):
                if campo in datos:
                    try:
                        leer_temario(datos[campo])
                    except ValidationError as error:
                        self.add_error(campo, error)
            if datos.get("veedor_presencia") == "presente" and not datos.get("veedor_id"):
                self.add_error("veedor_id", "Identificá al veedor presente.")
            if datos.get("veedor_presencia") == "sin_designacion" and not datos.get("oficio_veedor"):
                self.add_error("oficio_veedor", "Indicá el oficio que acredita la invitación a APUNSJ.")
            if datos.get("fecha_oposicion") and datos.get("fecha_sorteo_tema") and datos.get("hora_sorteo_tema") and datos.get("hora_oposicion"):
                from datetime import datetime, timedelta
                inicio = datetime.combine(datos["fecha_sorteo_tema"], datos["hora_sorteo_tema"])
                examen = datetime.combine(datos["fecha_oposicion"], datos["hora_oposicion"])
                if examen - inicio < timedelta(hours=72):
                    self.add_error("fecha_oposicion", "La prueba debe permitir la notificación del tema con 72 horas de anticipación.")
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
