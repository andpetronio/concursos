from django import forms
from core.fields import IdentificadorField

from .choices import EstadoConcurso, ModalidadConcurso, SituacionAdministrativa
from .models import Concurso
from .catalogos import AGRUPAMIENTOS, CATEGORIAS, categorias_para, opciones_dependientes, tramo_para
from django.core.exceptions import ValidationError


class ConcursoForm(forms.ModelForm):
    expediente = IdentificadorField(formato="expediente", max_length=100)
    agrupamiento = forms.ChoiceField(choices=[("", "Seleccioná un agrupamiento"), *AGRUPAMIENTOS])
    categoria = forms.ChoiceField(label="Categoría")
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput, required=False)

    class Meta:
        model = Concurso
        fields = Concurso.DATOS_EDITABLES
        widgets = {
            "funciones": forms.Textarea(attrs={"rows": 4}),
            "cadena_jerarquica": forms.Textarea(attrs={"rows": 2}),
            "detalle_vacancia": forms.Textarea(attrs={"rows": 2}),
            "fecha_baja": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        help_texts = {
            "cadena_jerarquica": "Nombre de la dependencia superior, sin artículos. Ej.: Dirección General de Contabilidad y Finanzas.",
            "unidad": "Nombre sin artículo. Ej.: Departamento de Patrimonio.",
            "dependencia": "Nombre sin artículo. Ej.: Dirección de Contabilidad.",
            "iniciador_nombre": "Nombre y apellido, sin artículos ni cargo.",
            "iniciador_cargo": "Cargo del iniciador, sin artículos.",
            "fecha_baja": "Fecha desde la cual se encuentra vacante el cargo, cuando conste.",
            "resolucion_baja": "Resolución del Rectorado. Ejemplo: 3278/26-R.",
            "fecha_baja": "Opcional. Fecha que consta en el acto o antecedente de baja.",
            "motivo_baja": "Antecedente textual histórico, opcional. Para convocatorias nuevas seleccioná la causa de vacancia.",
            "causa_vacancia": "Seleccioná el antecedente acreditado. No se presume la jubilación.",
            "acto_vacancia": "Consigná el acto acreditado de creación o traslado, cuando corresponda.",
            "detalle_vacancia": "Solo para Otra causa: redacción fundamentada para revisión en Word.",
            "turno_trabajo": "Determina automáticamente el horario del anexo: mañana 7 a 14 hs, tarde 14 a 21 hs.",
            "domicilio_trabajo": "Opcional. Dirección donde se desempeñarán las funciones; se reutiliza en el anexo.",
            "iniciador_tratamiento": "Tratamiento registrado en la nota de inicio (Sr., Sra., Dr., etc.). El artículo se selecciona aparte.",
            "resolucion_convocatoria": "Número oficial emitido por Rectorado (ej.: 3278/26-R). No registrar el número de un proyecto.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        codigo = self["agrupamiento"].value() or ""
        permitidas = categorias_para(codigo)
        opciones = [(n, n) for n in permitidas] if self.is_bound and permitidas else CATEGORIAS
        self.fields["categoria"].choices = [("", "Seleccioná una categoría"), *opciones]
        # Cada POST se valida con las categorías del agrupamiento enviado.
        self.fields["modalidad"].choices = [("", "Seleccioná un tipo de concurso"), *ModalidadConcurso.choices]
        self.fields["categoria"].widget.attrs["data-dependent-category"] = ""
        self.catalogo_cargos = opciones_dependientes()
        if self.instance.pk:
            self.fields["expediente"].conservar_actual(self.instance.expediente)
            self.fields["version_esperada"].required = True
            self.initial["version_esperada"] = self.instance.version

    def clean(self):
        datos = super().clean()
        # El tramo anterior no es una entrada editable. Django deriva el nuevo.
        self.instance.tramo = ""
        return datos

    @property
    def tramo_calculado(self):
        try:
            return tramo_para(self["agrupamiento"].value(), self["categoria"].value())
        except ValidationError:
            return "Seleccioná agrupamiento y categoría"


class FiltroConcursosForm(forms.Form):
    q = forms.CharField(label="Buscar", max_length=200, required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Expediente, cargo o código"}))
    estado = forms.ChoiceField(label="Estado principal", required=False,
                               choices=[("", "Todos los estados"), *EstadoConcurso.choices])


class CambioEstadoForm(forms.Form):
    estado = forms.ChoiceField(label="Estado principal", choices=EstadoConcurso.choices)
    situacion = forms.ChoiceField(label="Situación administrativa", choices=SituacionAdministrativa.choices)
    justificacion = forms.CharField(label="Justificación (opcional)", required=False, max_length=2000,
                                    widget=forms.Textarea(attrs={"rows": 4}))
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
