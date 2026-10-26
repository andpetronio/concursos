from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import RegexValidator
from django.urls import reverse
from core.validators import validar_cambio, validar_expediente

from .choices import EstadoConcurso, ModalidadConcurso, SituacionAdministrativa
from .catalogos import AGRUPAMIENTOS, CATEGORIAS, tramo_para


class Concurso(models.Model):
    # Datos propios del concurso, sin vínculos con catálogos externos mutables.
    DATOS_EDITABLES = (
        "expediente", "modalidad", "denominacion", "funciones", "agrupamiento",
        "categoria", "codigo_presupuestario", "unidad", "dependencia",
        "cadena_jerarquica", "ex_titular", "fecha_baja", "motivo_baja",
        "resolucion_baja", "iniciador_tratamiento", "iniciador_nombre", "iniciador_cargo",
        "turno_trabajo", "domicilio_trabajo", "jurisdiccion", "articulo_unidad",
        "articulo_dependencia", "articulo_superior", "articulo_iniciador",
        "causa_vacancia", "acto_vacancia", "detalle_vacancia",
        "resolucion_convocatoria",
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
    ex_titular = models.CharField("ex titular del cargo", max_length=200, blank=True)
    fecha_baja = models.DateField("fecha de vacancia", null=True, blank=True)
    motivo_baja = models.CharField("motivo de baja", max_length=500, blank=True)
    resolucion_baja = models.CharField(
        "resolución de baja (NNNN/NN-R)", max_length=9, blank=True,
        validators=[RegexValidator(r"^[0-9]{4}/[0-9]{2}-R$",
                                   "Utilizá el formato 3278/26-R (resolución del Rectorado).")],
    )
    iniciador_tratamiento = models.CharField("tratamiento del iniciador", max_length=80, blank=True)
    iniciador_nombre = models.CharField("nombre y apellido del iniciador", max_length=200, blank=True)
    iniciador_cargo = models.CharField("cargo del iniciador", max_length=200, blank=True)
    TURNO_TRABAJO = (("manana", "Mañana (7 a 14 hs)"), ("tarde", "Tarde (14 a 21 hs)"))
    turno_trabajo = models.CharField("turno de trabajo", max_length=10, choices=TURNO_TRABAJO, blank=True)
    domicilio_trabajo = models.CharField("domicilio de trabajo", max_length=250, blank=True)
    # Los nombres se almacenan sin artículos; el selector se reutiliza en la redacción.
    ARTICULOS = (("", "Sin artículo"), ("el", "el"), ("la", "la"),
                 ("del", "del"), ("de la", "de la"))
    articulo_unidad = models.CharField("artículo de la unidad", max_length=5, blank=True, choices=ARTICULOS)
    articulo_dependencia = models.CharField("artículo de la dependencia inmediata", max_length=5, blank=True, choices=ARTICULOS)
    articulo_superior = models.CharField("artículo de la dependencia superior", max_length=5, blank=True, choices=ARTICULOS)
    articulo_iniciador = models.CharField("artículo del iniciador", max_length=5, blank=True, choices=ARTICULOS)
    JURISDICCIONES = (
        ("rectorado", "Rectorado"),
        ("comercio", 'IPU - Escuela de Comercio "Lib. Gral. San Martín"'),
        ("industrial", 'IPU - Escuela Industrial "Domingo F. Sarmiento"'),
        ("central", 'IPU - Colegio Central Universitario "Mariano Moreno"'),
    )
    jurisdiccion = models.CharField("jurisdicción", max_length=20, choices=JURISDICCIONES, blank=True)
    CAUSAS_VACANCIA = (
        ("", "Seleccioná una causa"), ("nuevo", "Cargo nuevo"),
        ("jubilacion", "Jubilación"), ("renuncia", "Renuncia"),
        ("fallecimiento", "Fallecimiento"),
        ("concurso", "Designación por concurso en otro cargo"),
        ("efectivizacion", "Efectivización en otro cargo"),
        ("otra", "Otra causa"),
    )
    causa_vacancia = models.CharField("causa de vacancia", max_length=20, blank=True, choices=CAUSAS_VACANCIA)
    acto_vacancia = models.CharField("acto de creación o traslado", max_length=150, blank=True,
        help_text="Consigná el acto que conste en el expediente; no se presume resolución de baja.")
    detalle_vacancia = models.TextField("descripción de otra causa", max_length=1000, blank=True)
    resolucion_convocatoria = models.CharField(
        "resolución oficial de convocatoria", max_length=9, blank=True,
        validators=[RegexValidator(
            r"^[0-9]{4}/[0-9]{2}-R$",
            "Utilizá el formato 3278/26-R (resolución emitida por Rectorado).",
        )],
        help_text="Completá este dato solo cuando la resolución de convocatoria haya sido efectivamente emitida.",
    )
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
