from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from concursos.models import Concurso
from core.validators import normalizar_dni, normalizar_telefono, validar_cambio, validar_expediente


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


class JuradosVigentes(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(vigente=True)


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
    vigente = models.BooleanField(default=True, editable=False)
    objects = JuradosVigentes()
    todos = models.Manager()

    def clean(self):
        super().clean()
        if self.vigente and Jurado.todos.filter(
            concurso=self.concurso, representacion=self.representacion,
            calidad=self.calidad, vigente=True,
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                "Ya hay un integrante del jurado registrado para esa representación y calidad en este concurso."
            )
        if self.telefono:
            try:
                self.telefono = validar_cambio(self, "telefono", normalizar_telefono)
            except ValidationError as error:
                raise ValidationError({"telefono": error})

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
                                    condition=models.Q(vigente=True), name="jurado_plaza_vigente_unica"),
            models.CheckConstraint(condition=models.Q(representacion__in=["dependencia", "rectorado", "personal"]),
                                   name="jurado_representacion_valida"),
            models.CheckConstraint(condition=models.Q(calidad__in=["titular", "suplente"]), name="jurado_calidad_valida"),
        ]


class ActuacionJurado(models.Model):
    """Bitácora inmutable de actuaciones y cambios de integración del jurado."""
    class Tipo(models.TextChoices):
        PRESENTACION = "presentacion", "Presentación recibida"
        CESE = "cese", "Cese por resolución"
        PROMOCION = "promocion", "Designación de suplente como titular"
        DESIGNACION = "designacion", "Nueva designación"

    class Motivo(models.TextChoices):
        EXCUSACION = "excusacion", "Excusación"
        RECUSACION = "recusacion", "Recusación"

    concurso = models.ForeignKey(Concurso, on_delete=models.PROTECT, related_name="actuaciones_jurado")
    jurado = models.ForeignKey(Jurado, on_delete=models.PROTECT, related_name="actuaciones")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    motivo = models.CharField(max_length=20, choices=Motivo.choices, blank=True)
    representacion = models.CharField(max_length=20, choices=Jurado.Representacion.choices)
    calidad_anterior = models.CharField(max_length=10, choices=Jurado.Calidad.choices, blank=True)
    calidad_nueva = models.CharField(max_length=10, choices=Jurado.Calidad.choices, blank=True)
    fecha_actuacion = models.DateField()
    resolucion = models.CharField(max_length=60, blank=True)
    fojas = models.CharField(max_length=50, blank=True)
    observaciones = models.TextField(max_length=1000, blank=True)
    antecedente = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="movimientos_derivados")
    resuelto_por = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="presentaciones_resueltas")
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registrado_en", "-pk"]
        default_permissions = ()


class Veedor(Participacion):
    cargo = models.CharField(max_length=150, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    def clean(self):
        super().clean()
        if self.telefono:
            try:
                self.telefono = validar_cambio(self, "telefono", normalizar_telefono)
            except ValidationError as error:
                raise ValidationError({"telefono": error})

    class Meta:
        ordering = ["pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["concurso", "persona"], name="veedor_persona_unica")]


class Aspirante(Participacion):
    class Situacion(models.TextChoices):
        INSCRIPTO = "inscripto", "Inscripto"
        IMPUGNACION_PENDIENTE = "impugnacion_pendiente", "Impugnación en trámite"
        NO_HABILITADO = "no_habilitado", "No habilitado para oposición"
        EXCLUIDO = "excluido", "Excluido por decisión de la autoridad"
        DESISTIO = "desistio", "Desistió"

    situacion = models.CharField(max_length=30, choices=Situacion, default=Situacion.INSCRIPTO)

    @property
    def puede_rendir(self):
        return self.situacion in (self.Situacion.INSCRIPTO, self.Situacion.IMPUGNACION_PENDIENTE)

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


class CambioSituacionAspirante(models.Model):
    """Historial inmutable de actuaciones acreditadas sobre cada inscripción."""

    class Tipo(models.TextChoices):
        IMPUGNACION = "impugnacion", "Registrar impugnación en trámite"
        NO_HABILITACION = "no_habilitacion", "No habilitar para la oposición (Jurado, art. 34)"
        EXCLUSION = "exclusion", "Registrar exclusión por impugnación resuelta"
        DESISTIMIENTO = "desistimiento", "Registrar desistimiento"
        RECTIFICACION = "rectificacion", "Rectificar o dejar sin efecto la decisión"

    aspirante = models.ForeignKey(Aspirante, on_delete=models.PROTECT, related_name="historial_situacion")
    tipo = models.CharField(max_length=20, choices=Tipo)
    anterior = models.CharField(max_length=30, choices=Aspirante.Situacion)
    nueva = models.CharField(max_length=30, choices=Aspirante.Situacion)
    fecha_decision = models.DateField("fecha de la actuación")
    class Documento(models.TextChoices):
        ACTA = "acta", "Acta del Jurado"
        RESOLUCION = "resolucion", "Resolución de la autoridad"
        NOTA = "nota", "Nota o presentación"
        OTRO = "otro", "Otra actuación formal"

    clase_documento = models.CharField(max_length=20, choices=Documento)
    documento = models.CharField("actuación respaldatoria", max_length=250)
    fojas = models.CharField("fojas del expediente", max_length=50)
    fundamento = models.TextField(max_length=1500)
    constancia_comunicacion = models.CharField(max_length=300, blank=True)
    version = models.PositiveIntegerField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registrado_en", "-pk"]
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["aspirante", "version"],
                                               name="aspirante_situacion_historial_version_unica")]


class EvaluacionAspirante(models.Model):
    """Puntajes acreditados por el jurado; no constituyen un dictamen por sí solos."""

    aspirante = models.OneToOneField(Aspirante, on_delete=models.PROTECT, related_name="evaluacion")
    antecedentes = models.DecimalField("puntaje de antecedentes", max_digits=5, decimal_places=2)
    oposicion = models.DecimalField("puntaje de oposición", max_digits=5, decimal_places=2)
    version = models.PositiveIntegerField(default=1, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluaciones_creadas")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluaciones_actualizadas")

    class Meta:
        default_permissions = ()

    @property
    def total(self):
        return self.antecedentes + self.oposicion

    def clean(self):
        super().clean()
        from .evaluaciones import MAX_ANTECEDENTES, MAX_OPOSICION
        for nombre, maximo in (("antecedentes", MAX_ANTECEDENTES), ("oposicion", MAX_OPOSICION)):
            valor = getattr(self, nombre, None)
            if valor is not None and not (0 <= valor <= maximo):
                raise ValidationError({nombre: f"El puntaje debe estar entre 0 y {maximo}."})


class CambioEvaluacion(models.Model):
    """Auditoría de correcciones, sin sobrescribir el antes/después."""

    evaluacion = models.ForeignKey(EvaluacionAspirante, on_delete=models.PROTECT, related_name="cambios")
    antecedentes_antes = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    oposicion_antes = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    antecedentes_despues = models.DecimalField(max_digits=5, decimal_places=2)
    oposicion_despues = models.DecimalField(max_digits=5, decimal_places=2)
    motivo = models.TextField(max_length=1000, blank=True)
    version = models.PositiveIntegerField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        default_permissions = ()
