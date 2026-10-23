import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from concursos.models import Concurso


def normalizar_dni(valor):
    valor = str(valor).strip()
    if not valor or not re.fullmatch(r"[0-9.\s-]+", valor):
        raise ValidationError("Ingresá un DNI formado por números; podés usar puntos o guiones.")
    dni = re.sub(r"\D", "", valor)
    if not dni or len(dni) > 12:
        raise ValidationError("Ingresá un DNI válido de hasta 12 dígitos.")
    return dni


class Persona(models.Model):
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    dni = models.CharField(max_length=12, unique=True, verbose_name="DNI")
    version = models.PositiveIntegerField(default=1, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name="personas_creadas")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name="personas_actualizadas")

    class Meta:
        ordering = ["apellido", "nombre", "pk"]
        default_permissions = ()

    def clean(self):
        super().clean()
        self.dni = normalizar_dni(self.dni)

    def save(self, *args, **kwargs):
        self.dni = normalizar_dni(self.dni)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class Participacion(models.Model):
    concurso = models.ForeignKey(Concurso, on_delete=models.PROTECT, related_name="%(class)ss")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="%(class)ss")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name="%(class)ss_creados")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name="%(class)ss_actualizados")

    class Meta:
        abstract = True


class Jurado(Participacion):
    class Representacion(models.TextChoices):
        DEPENDENCIA = "dependencia", "Autoridad de dependencia convocante"
        RECTORADO = "rectorado", "Rectorado"
        PERSONAL = "personal", "Personal de dependencia"

    class Calidad(models.TextChoices):
        TITULAR = "titular", "Titular"
        SUPLENTE = "suplente", "Suplente"

    representacion = models.CharField(max_length=20, choices=Representacion)
    calidad = models.CharField(max_length=10, choices=Calidad)
    titulo = models.CharField("título", max_length=150)
    cargo = models.CharField(max_length=150)
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    def unique_error_message(self, model_class, unique_check):
        if model_class is Jurado and set(unique_check) == {"concurso", "representacion", "calidad"}:
            return ValidationError(
                "Ya hay un integrante del jurado registrado para esa representación y calidad en este concurso.",
                code="unique_together",
            )
        return super().unique_error_message(model_class, unique_check)

    class Meta:
        ordering = ["representacion", "calidad", "pk"]
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=["concurso", "representacion", "calidad"],
                                    name="jurado_plaza_unica"),
            models.CheckConstraint(condition=models.Q(representacion__in=["dependencia", "rectorado", "personal"]),
                                   name="jurado_representacion_valida"),
            models.CheckConstraint(condition=models.Q(calidad__in=["titular", "suplente"]), name="jurado_calidad_valida"),
        ]


class Veedor(Participacion):
    cargo = models.CharField(max_length=150, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        ordering = ["pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["concurso", "persona"], name="veedor_persona_unica")]


class Aspirante(Participacion):
    class Meta:
        ordering = ["persona__apellido", "persona__nombre", "pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["concurso", "persona"], name="aspirante_persona_unica")]
