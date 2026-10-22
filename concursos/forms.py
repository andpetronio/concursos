from django import forms

from .choices import EstadoConcurso, SituacionAdministrativa
from .models import Concurso


class ConcursoForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput, required=False)

    class Meta:
        model = Concurso
        fields = Concurso.DATOS_EDITABLES
        widgets = {
            "funciones": forms.Textarea(attrs={"rows": 4}),
            "cadena_jerarquica": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "modalidad": "Transcribí la modalidad aplicable, sin seleccionar un catálogo.",
            "cadena_jerarquica": "Registrá la estructura aplicable a este concurso, desde la unidad hasta la dependencia.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["version_esperada"].required = True
            self.initial["version_esperada"] = self.instance.version


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
