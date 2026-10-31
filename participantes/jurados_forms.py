from django import forms
from core.fields import ResolucionRectoralField

from .models import ActuacionJurado, Jurado
from .forms import JuradoAltaForm
from expedientes.validators import normalizar_fojas


class FojasJuradoMixin:
    def clean_fojas(self):
        return normalizar_fojas(self.cleaned_data["fojas"])


class PresentacionJuradoForm(FojasJuradoMixin, forms.Form):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    motivo = forms.ChoiceField(label="Motivo", choices=ActuacionJurado.Motivo.choices)
    fecha_actuacion = forms.DateField(label="Fecha de presentación", widget=forms.DateInput(attrs={"type": "date"}))
    fojas = forms.CharField(label="Fojas de la actuación", max_length=50, required=False)
    observaciones = forms.CharField(required=False, max_length=1000,
                                    widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, jurado, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = jurado.version


class PresentacionPendienteField(forms.ModelChoiceField):
    """Muestra la actuación administrativa, no el nombre técnico del modelo."""

    def label_from_instance(self, actuacion):
        motivo = actuacion.get_motivo_display()
        fecha = actuacion.fecha_actuacion.strftime("%d/%m/%Y")
        fojas = f"fojas {actuacion.fojas}" if actuacion.fojas else "fojas sin registrar"
        return f"{motivo} presentada el {fecha} ({fojas})"


class ResolucionJuradoForm(FojasJuradoMixin, forms.Form):
    version_esperada = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    presentacion_id = PresentacionPendienteField(
        label="Presentación a resolver", queryset=ActuacionJurado.objects.none(),
        empty_label="Seleccioná una presentación pendiente",
    )
    resolucion = ResolucionRectoralField(label="Resolución rectoral (N.º y año)")
    fecha_resolucion = forms.DateField(label="Fecha de la resolución", widget=forms.DateInput(attrs={"type": "date"}))
    fojas = forms.CharField(label="Fojas de la resolución", max_length=50, required=False)
    observaciones = forms.CharField(required=False, max_length=1000,
                                    widget=forms.Textarea(attrs={"rows": 3}))
    promover_suplente = forms.BooleanField(required=False, label="Designar al suplente como nuevo titular")

    def __init__(self, *args, jurado, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["version_esperada"] = jurado.version
        self.fields["presentacion_id"].queryset = ActuacionJurado.objects.filter(
            jurado=jurado, tipo="presentacion", resuelto_por__isnull=True,
        )
        if jurado.calidad == Jurado.Calidad.TITULAR:
            suplente = Jurado.objects.filter(concurso=jurado.concurso, representacion=jurado.representacion,
                                             calidad=Jurado.Calidad.SUPLENTE).exists()
            self.initial["promover_suplente"] = suplente
            if suplente:
                self.fields["promover_suplente"].help_text = "Obligatorio: la plaza titular se libera antes de la promoción."
            else:
                self.fields.pop("promover_suplente")
        else:
            self.fields.pop("promover_suplente")


class ReemplazoJuradoForm(FojasJuradoMixin, JuradoAltaForm):
    representacion = None
    calidad = None
    resolucion = ResolucionRectoralField(label="Resolución rectoral (N.º y año)")
    fecha_resolucion = forms.DateField(label="Fecha de la resolución", widget=forms.DateInput(attrs={"type": "date"}))
    fojas = forms.CharField(label="Fojas de la resolución", max_length=50, required=False)
    observaciones = forms.CharField(required=False, max_length=1000,
                                    widget=forms.Textarea(attrs={"rows": 3}))
