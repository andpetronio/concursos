from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from core.validators import validar_cambio, validar_expediente

from .choices import EstadoConcurso, ModalidadConcurso, SituacionAdministrativa
from .catalogos import AGRUPAMIENTOS, CATEGORIAS, tramo_para


class Concurso(models.Model):
    # Datos propios del concurso, sin vínculos con catálogos externos mutables.
    DATOS_EDITABLES = (
        "expediente", "modalidad", "denominacion", "funciones", "agrupamiento",
        "categoria", "codigo_presupuestario", "unidad", "dependencia",
        "cadena_jerarquica",
    )

    expediente = models.CharField("expediente", max_length=100)
    modalidad = models.CharField("tipo de concurso", max_length=100, choices=ModalidadConcurso)
    denominacion = models.CharField("denominación del cargo", max_length=200)
    funciones = models.TextField("funciones del cargo", max_length=4000, blank=True)
    agrupamiento = models.CharField("agrupamiento", max_length=100, choices=AGRUPAMIENTOS)
    categoria = models.CharField("categoría", max_length=50, choices=CATEGORIAS)
    tramo = models.CharField("tramo", max_length=100, blank=True, editable=False)
    clasificacion_anterior = models.JSONField(default=dict, blank=True, editable=False)
    codigo_presupuestario = models.CharField("código presupuestario", max_length=100)
    unidad = models.CharField("unidad", max_length=200)
    dependencia = models.CharField("dependencia", max_length=200)
    cadena_jerarquica = models.TextField("cadena jerárquica", max_length=2000)
    estado = models.CharField("estado principal", max_length=20, choices=EstadoConcurso,
                              default=EstadoConcurso.PREPARACION, db_index=True)
    situacion = models.CharField("situación administrativa", max_length=20,
                                 choices=SituacionAdministrativa, default=SituacionAdministrativa.NORMAL)
    creado_en = models.DateTimeField("fecha de creación", auto_now_add=True)
    actualizado_en = models.DateTimeField("última modificación", auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="concursos_creados", verbose_name="creado por")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        related_name="concursos_actualizados", verbose_name="modificado por")
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        ordering = ["-creado_en", "-pk"]
        verbose_name = "concurso"
        verbose_name_plural = "concursos"
        default_permissions = ("add", "change", "view")
        permissions = [("cambiar_estado_concurso", "Puede cambiar el estado y la situación de un concurso")]
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=EstadoConcurso.values), name="concurso_estado_valido"),
            models.CheckConstraint(condition=models.Q(situacion__in=SituacionAdministrativa.values), name="concurso_situacion_valida"),
        ]

    def __str__(self):
        return f"{self.expediente} · {self.denominacion}"

    def clean(self):
        super().clean()
        errores = {}
        if self.expediente:
            try:
                validar_cambio(self, "expediente", validar_expediente)
            except ValidationError as error:
                errores["expediente"] = error
        if self.agrupamiento and self.categoria:
            try:
                esperado = tramo_para(self.agrupamiento, self.categoria)
                if self.tramo and self.tramo != esperado:
                    errores["tramo"] = "El tramo no corresponde al agrupamiento y categoría."
                else:
                    self.tramo = esperado
            except ValidationError as error:
                errores["categoria"] = error
        if errores:
            raise ValidationError(errores)

    def get_absolute_url(self):
        return reverse("concursos:detalle", args=[self.pk])


class CambioEstado(models.Model):
    concurso = models.ForeignKey(Concurso, on_delete=models.PROTECT, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    estado_anterior = models.CharField(max_length=20, choices=EstadoConcurso, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=EstadoConcurso)
    situacion_anterior = models.CharField(max_length=20, choices=SituacionAdministrativa, blank=True)
    situacion_nueva = models.CharField(max_length=20, choices=SituacionAdministrativa)
    justificacion = models.TextField("justificación", max_length=2000, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "cambio de estado"
        verbose_name_plural = "historial de estados"
        default_permissions = ()
