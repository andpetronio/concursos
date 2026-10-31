from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DestinatarioAPUNSJ(models.Model):
    tratamiento = models.CharField(max_length=4, choices=[("Sr.", "Sr."), ("Sra.", "Sra.")])
    cargo = models.CharField(max_length=30, choices=[("Secretario General", "Secretario General"),
                                                  ("Secretaria General", "Secretaria General")])
    titulo = models.CharField("título profesional", max_length=100, blank=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="destinatarios_creados")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="destinatarios_actualizados")

    class Meta:
        default_permissions = ()
        permissions = [("configurar_institucion", "Puede modificar el destinatario institucional de APUNSJ")]
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="apunsj_destinatario_unico")]

    def clean(self):
        super().clean()
        correspondencia = {"Sr.": "Secretario General", "Sra.": "Secretaria General"}
        if correspondencia.get(self.tratamiento) != self.cargo:
            raise ValidationError({"cargo": "El cargo debe corresponder al tratamiento seleccionado."})
        for campo in ("nombre", "apellido"):
            if not getattr(self, campo).strip():
                raise ValidationError({campo: "Este dato es obligatorio."})


class DestinatarioPersonal(models.Model):
    """Jefatura de Personal que recibe el oficio de elección por el estamento."""
    id = models.BigAutoField(primary_key=True, serialize=False)
    tratamiento = models.CharField(max_length=4, choices=[("Sr.", "Sr."), ("Sra.", "Sra.")])
    cargo = models.CharField(max_length=45, choices=[
        ("Jefe del Departamento de Personal", "Jefe del Departamento de Personal"),
        ("Jefa del Departamento de Personal", "Jefa del Departamento de Personal"),
    ])
    titulo = models.CharField("título profesional", max_length=100, blank=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="personal_destinatario_unico")]

    def clean(self):
        super().clean()
        correctos = {"Sr.": "Jefe del Departamento de Personal", "Sra.": "Jefa del Departamento de Personal"}
        if correctos.get(self.tratamiento) != self.cargo:
            raise ValidationError({"cargo": "El cargo debe corresponder al tratamiento seleccionado."})
        for campo in ("nombre", "apellido"):
            if not getattr(self, campo).strip():
                raise ValidationError({campo: "Este dato es obligatorio."})


class RegistroInmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Las generaciones documentales no se modifican.")

    def delete(self):
        raise ValidationError("Las generaciones documentales no se eliminan.")


class GeneracionDocumento(models.Model):
    concurso = models.ForeignKey("concursos.Concurso", on_delete=models.PROTECT, related_name="documentos_generados")
    tipo = models.CharField(max_length=40)
    plantilla_version = models.CharField(max_length=40)
    instantanea = models.JSONField()
    contenido = models.BinaryField(editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    generado_en = models.DateTimeField(auto_now_add=True)
    objects = RegistroInmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-generado_en", "-pk"]
        default_permissions = ()
        permissions = [("generar_documento", "Puede generar y descargar documentos de concursos")]

    @property
    def nombre_tipo(self):
        from .registry import POR_CODIGO
        tipo = POR_CODIGO.get(self.tipo)
        if self.tipo == "solicitud_jurados_rectorado":
            return "Oficio al Rector solicitando jurados (histórico)"
        return tipo.nombre if tipo else "Documento histórico"

    def save(self, *args, **kwargs):
        if not self._state.adding or self.pk is not None:
            raise ValidationError("Las generaciones documentales no se modifican ni reemplazan.")
        kwargs["force_insert"] = True
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las generaciones documentales no se eliminan.")


class MembreteInstitucional(models.Model):
    """Imagen vigente para oficios y notificaciones, conservada en PostgreSQL."""
    contenido = models.BinaryField(editable=False)
    nombre_archivo = models.CharField(max_length=150)
    tipo_mime = models.CharField(max_length=20)
    sha256 = models.CharField(max_length=64, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="membrete_institucional_unico")]

    def save(self, *args, **kwargs):
        if self.pk is not None and self.pk != 1:
            raise ValidationError("Solo se permite un membrete institucional vigente.")
        return super().save(*args, **kwargs)
