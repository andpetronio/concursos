from django.db import models


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
