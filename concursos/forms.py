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
            "cadena_jerarquica": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "cadena_jerarquica": "Registrá la estructura aplicable a este concurso, desde la unidad hasta la dependencia.",
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
