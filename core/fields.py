import re

from django import forms
from django.core.exceptions import ValidationError

from .validators import normalizar_dni, validar_expediente, normalizar_telefono


class IdentificadorInput(forms.TextInput):
    template_name = "core/widgets/identificador.html"


    def format_value(self, value):
        value = super().format_value(value)
        if self.attrs.get("data-mask") == "dni" and value and re.fullmatch(r"[0-9]{8}", value):
            return f"{value[:2]}.{value[2:5]}.{value[5:]}"
        return value


class IdentificadorField(forms.CharField):
    """Comparte validación y contrato HTML; permite conservar solo el valor histórico."""
    def __init__(self, *, formato, **kwargs):
        self.normalizar = normalizar_dni if formato == "dni" else validar_expediente
        self.valor_anterior = None
        attrs = {"inputmode": "numeric" if formato == "dni" else "text", "data-mask": formato,
                 "maxlength": 10 if formato == "dni" else 12}
        if formato == "dni":
            kwargs.setdefault("label", "DNI")
            kwargs.setdefault("help_text", "Exactamente 8 dígitos. Podés pegar el DNI con o sin puntos.")
            attrs.update(placeholder="99.999.999", pattern=r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}|[0-9]{8}")
        else:
            kwargs.setdefault("help_text", "Ejemplo: 01-758-2026. Separá el número del año con un guion.")
            attrs.update(placeholder="01-758-2026", pattern="[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}")
        kwargs["widget"] = IdentificadorInput(attrs=attrs)
        super().__init__(**kwargs)
        # Django agrega su propio maxlength usando max_length del formulario (legado).
        # El límite visible solicitado es distinto y no reduce la columna histórica.
        self.widget.attrs["maxlength"] = 10 if formato == "dni" else 12

    def conservar_actual(self, valor):
        if not valor:
            return
        try:
            self.normalizar(valor)
        except ValidationError:
            self.valor_anterior = valor
            self.widget.attrs["data-legacy-value"] = valor
            self.widget.attrs["pattern"] += "|" + re.escape(valor)
            self.help_text += " El valor histórico puede conservarse; si lo cambiás, usá el formato indicado."

    def clean(self, value):
        value = super().clean(value)
        if not value or value == self.valor_anterior:
            return value
        return self.normalizar(value)


class TelefonoInput(forms.TextInput):
    input_type = "tel"

    def __init__(self, attrs=None):
        super().__init__({"data-mask": "telefono", "inputmode": "tel", "maxlength": 11,
                          "placeholder": "999-9999999", "pattern": r"[0-9]{3}-[0-9]{7}", **(attrs or {})})


class TelefonoField(forms.CharField):
    """Normaliza altas y permite conservar valores históricos al editar otros datos."""
    def __init__(self, **kwargs):
        kwargs.setdefault("label", "Teléfono")
        kwargs.setdefault("max_length", 40)  # No reducir la columna histórica.
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", TelefonoInput)
        super().__init__(**kwargs)
        self.widget.attrs["maxlength"] = 11
        self.valor_anterior = None

    def conservar_actual(self, valor):
        if not valor:
            return
        try:
            normalizar_telefono(valor)
        except ValidationError:
            self.valor_anterior = valor
            self.widget.attrs["data-legacy-value"] = valor
            self.widget.attrs["pattern"] += "|" + re.escape(valor)
            self.help_text = "Valor histórico: podés conservarlo sin cambios o cargar un teléfono con el formato indicado."

    def clean(self, value):
        value = super().clean(value)
        if not value or value == self.valor_anterior:
            return value
        return normalizar_telefono(value)

class ResolucionRectoralField(forms.CharField):
    """Entrada compartida para números oficiales del Rectorado: NNNN/NN-R."""

    def __init__(self, **kwargs):
        from django.core.validators import RegexValidator

        kwargs.setdefault("max_length", 9)
        kwargs.setdefault("help_text", "Formato: 3278/26-R.")
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "data-mask": "resolucion",
            "inputmode": "text",
            "maxlength": 9,
            "placeholder": "3278/26-R",
            "pattern": r"[0-9]{4}/[0-9]{2}-R",
            "autocomplete": "off",
        }))
        validators = list(kwargs.pop("validators", []))
        validators.append(RegexValidator(
            r"^[0-9]{4}/[0-9]{2}-R$",
            "Utilizá el formato 3278/26-R (resolución del Rectorado).",
        ))
        kwargs["validators"] = validators
        super().__init__(**kwargs)

