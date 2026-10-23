from django import forms

from .models import ControlDocumental, SeguimientoDocumental
from .validators import normalizar_fojas


class ControlDocumentalForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = ControlDocumental
        fields = ("verificado", "fojas", "observaciones")
        widgets = {
            "fojas": forms.TextInput(attrs={"placeholder": "5 o 5/8"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {"fojas": "Una foja o un rango. Sin esta referencia el requisito permanece pendiente."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = self.instance.version
        self.fields["verificado"].widget.attrs["aria-label"] = f"Verificado: {self.instance.definicion.nombre}"
        if not self.instance.definicion.requiere_foja:
            del self.fields["fojas"]

    def clean_fojas(self):
        return normalizar_fojas(self.cleaned_data["fojas"])


class EtapaDocumentalForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = SeguimientoDocumental
        fields = ("etapa",)
        help_texts = {"etapa": "Los requisitos de esta etapa y de las anteriores son exigibles. Esta selección no cambia el estado administrativo."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = self.instance.version
