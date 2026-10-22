from django.conf import settings
from django.db import models
from django.urls import reverse

from .choices import EstadoConcurso, SituacionAdministrativa


class Concurso(models.Model):
    # Datos propios del concurso, sin vínculos con catálogos externos mutables.
    DATOS_EDITABLES = (
        "expediente", "modalidad", "denominacion", "funciones", "agrupamiento",
        "categoria", "tramo", "codigo_presupuestario", "unidad", "dependencia",
        "cadena_jerarquica",
    )

    expediente = models.CharField("expediente", max_length=100)
    modalidad = models.CharField("tipo / modalidad", max_length=100)
    denominacion = models.CharField("denominación del cargo", max_length=200)
    funciones = models.TextField("funciones del cargo", max_length=4000)
    agrupamiento = models.CharField("agrupamiento", max_length=100)
    categoria = models.CharField("categoría", max_length=50)
    tramo = models.CharField("tramo", max_length=100)
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
