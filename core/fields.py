import re

from django import forms
from django.core.exceptions import ValidationError

from .validators import normalizar_dni, validar_expediente


class IdentificadorInput(forms.TextInput):
    template_name = "core/widgets/identificador.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["es_expediente"] = self.attrs.get("data-mask") == "expediente"
        return context

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
        attrs = {"inputmode": "numeric", "data-mask": formato}
        if formato == "dni":
            kwargs.setdefault("label", "DNI")
            kwargs.setdefault("help_text", "Exactamente 8 dígitos. Podés pegar el DNI con o sin puntos.")
            attrs.update(placeholder="99.999.999", pattern=r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}|[0-9]{8}")
        else:
            kwargs.setdefault("help_text", "Formato 01-758-2026. El bloque central tiene entre 1 y 4 dígitos, sin ceros de relleno. Usá la tecla o el botón Agregar guion para cerrar ese bloque.")
            attrs.update(placeholder="01-758-2026", pattern="[0-9]{2}-[1-9][0-9]{0,3}-[0-9]{4}")
        kwargs["widget"] = IdentificadorInput(attrs=attrs)
        super().__init__(**kwargs)

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
