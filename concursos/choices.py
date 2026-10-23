from django.db import models


class ModalidadConcurso(models.TextChoices):
    CERRADO_INTERNO = "cerrado_interno", "Cerrado Interno"
    CERRADO_GENERAL = "cerrado_general", "Cerrado General"
    ABIERTO = "abierto", "Abierto"
    ACOTADO = "acotado", "Acotado"


class EstadoConcurso(models.TextChoices):
    PREPARACION = "preparacion", "Preparación"
    CONVOCADO = "convocado", "Convocado"
    EN_CURSO = "en_curso", "En curso"
    CON_DICTAMEN = "con_dictamen", "Con dictamen"
    FINALIZADO = "finalizado", "Finalizado"


class SituacionAdministrativa(models.TextChoices):
    NORMAL = "normal", "Normal"
    IMPUGNADO = "impugnado", "Impugnado"
    SUSPENDIDO = "suspendido", "Suspendido"
