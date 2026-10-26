from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .catalogo import OPCIONES_REQUISITO, POR_CODIGO, SECCIONES
from .validators import normalizar_fojas


class ControlDocumental(models.Model):
    concurso = models.ForeignKey("concursos.Concurso", on_delete=models.PROTECT, related_name="controles_documentales")
    requisito = models.CharField(max_length=40, choices=OPCIONES_REQUISITO)
    verificado = models.BooleanField("Verificado", default=False)
    fojas = models.CharField("Fojas", max_length=50, blank=True)
    partida_principal = models.CharField("Partida principal (2 dígitos)", max_length=2, blank=True)
    actividad_presupuestaria = models.CharField("Actividad (2 dígitos)", max_length=2, blank=True)
    observaciones = models.TextField("Observaciones", max_length=2000, blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="controles_verificados")
    verificado_en = models.DateTimeField(null=True, blank=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                        related_name="controles_modificados")
    actualizado_en = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        default_permissions = ("change",)
        verbose_name = "control documental"
        verbose_name_plural = "controles documentales"
        constraints = [
            models.UniqueConstraint(fields=["concurso", "requisito"], name="control_requisito_unico"),
            models.CheckConstraint(condition=models.Q(requisito__in=[c for c, _ in OPCIONES_REQUISITO]),
                                   name="control_requisito_valido"),
        ]

    @property
    def definicion(self):
        return POR_CODIGO[self.requisito]

    @property
    def completo(self):
        if not self.verificado:
            return False
        if not self.definicion.requiere_foja:
            return True
        try:
            return bool(normalizar_fojas(self.fojas))
        except ValidationError:
            return False

    def clean(self):
        super().clean()
        from .validators import normalizar_codigo_dos_digitos
        errores = {}
        for campo in ("partida_principal", "actividad_presupuestaria"):
            try:
                setattr(self, campo, normalizar_codigo_dos_digitos(getattr(self, campo)))
            except ValidationError as error:
                errores[campo] = error
        if errores:
            raise ValidationError(errores)
        if self.requisito != "afectacion_presupuestaria" and (
                self.partida_principal or self.actividad_presupuestaria):
            raise ValidationError("Los códigos presupuestarios solo se cargan en afectación presupuestaria.")
        try:
            self.fojas = normalizar_fojas(self.fojas)
        except ValidationError as error:
            raise ValidationError({"fojas": error})
        if self.requisito in POR_CODIGO and not self.definicion.requiere_foja and self.fojas:
            raise ValidationError("Este requisito se controla sin referencia de fojas.")


class CambioControlDocumental(models.Model):
    control = models.ForeignKey(ControlDocumental, on_delete=models.PROTECT, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    anterior = models.JSONField()
    nuevo = models.JSONField()

    class Meta:
        default_permissions = ()
        ordering = ["-fecha", "-pk"]
        constraints = [models.UniqueConstraint(fields=["control", "version"], name="control_historial_version_unica")]


class SeguimientoDocumental(models.Model):
    concurso = models.OneToOneField("concursos.Concurso", on_delete=models.PROTECT, related_name="seguimiento_documental")
    etapa = models.CharField("Etapa documental activa", max_length=20, choices=SECCIONES, default="preparacion")
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(etapa__in=[c for c, _ in SECCIONES]),
                                              name="etapa_documental_valida")]


class CambioEtapaDocumental(models.Model):
    seguimiento = models.ForeignKey(SeguimientoDocumental, on_delete=models.PROTECT, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    anterior = models.CharField(max_length=20, choices=SECCIONES)
    nueva = models.CharField(max_length=20, choices=SECCIONES)
    version = models.PositiveIntegerField()

    class Meta:
        default_permissions = ()
        ordering = ["-fecha", "-pk"]
        constraints = [models.UniqueConstraint(fields=["seguimiento", "version"], name="etapa_historial_version_unica")]
