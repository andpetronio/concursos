from django import forms

from .models import ControlDocumental, SeguimientoDocumental
from .validators import normalizar_fojas


class ControlDocumentalForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = ControlDocumental
        fields = ("verificado", "fojas", "partida_principal", "actividad_presupuestaria", "observaciones")
        widgets = {
            "fojas": forms.TextInput(attrs={"placeholder": "5 o 5/8"}),
            "partida_principal": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "2", "placeholder": "01"}),
            "actividad_presupuestaria": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "2", "placeholder": "02"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {"fojas": "Una foja o un rango. Sin esta referencia el requisito permanece pendiente."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = self.instance.version
        self.fields["partida_principal"].label = "Unidad principal presupuestaria (PPAL, 2 dígitos)"
        self.fields["partida_principal"].help_text = "Es el código PPAL de la tabla de afectación. No confundir con la partida de gasto 1.1, que es fija."
        self.fields["actividad_presupuestaria"].label = "Actividad presupuestaria (2 dígitos)"
        self.fields["verificado"].widget.attrs["aria-label"] = f"Verificado: {self.instance.definicion.nombre}"
        if not self.instance.definicion.requiere_foja:
            del self.fields["fojas"]
        if self.instance.requisito != "afectacion_presupuestaria":
            del self.fields["partida_principal"]
            del self.fields["actividad_presupuestaria"]

    def clean_fojas(self):
        return normalizar_fojas(self.cleaned_data["fojas"])

    def clean_partida_principal(self):
        from .validators import normalizar_codigo_dos_digitos
        return normalizar_codigo_dos_digitos(self.cleaned_data["partida_principal"])

    def clean_actividad_presupuestaria(self):
        from .validators import normalizar_codigo_dos_digitos
        return normalizar_codigo_dos_digitos(self.cleaned_data["actividad_presupuestaria"])


class EtapaDocumentalForm(forms.ModelForm):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)

    class Meta:
        model = SeguimientoDocumental
        fields = ("etapa",)
        help_texts = {"etapa": "Los requisitos de esta etapa y de las anteriores son exigibles. Esta selección no cambia el estado administrativo."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = self.instance.version
