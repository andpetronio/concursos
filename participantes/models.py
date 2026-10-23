from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from concursos.models import Concurso
from core.validators import normalizar_dni, validar_cambio, validar_expediente


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
        try:
            self.dni = validar_cambio(self, "dni", normalizar_dni)
        except ValidationError as error:
            raise ValidationError({"dni": error})

    def save(self, *args, **kwargs):
        self.dni = validar_cambio(self, "dni", normalizar_dni)
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
    unidad = models.CharField(
        "unidad", max_length=200,
        help_text="Indicá la unidad donde presta servicios el integrante; puede ser distinta de la dependencia del concurso.",
    )
    cargo = models.CharField(max_length=150, blank=True)
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
    email = models.EmailField("correo electrónico", blank=True)
    expediente_inscripcion = models.CharField("expediente de inscripción", max_length=100, blank=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    def clean(self):
        super().clean()
        if self.expediente_inscripcion:
            try:
                validar_cambio(self, "expediente_inscripcion", validar_expediente)
            except ValidationError as error:
                raise ValidationError({"expediente_inscripcion": error})

    class Meta:
        ordering = ["persona__apellido", "persona__nombre", "pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["concurso", "persona"], name="aspirante_persona_unica")]
