from django.contrib.sessions.models import Session
from django.db import models


class SessionActivity(models.Model):
    """Reloj compartido entre pestañas, independiente del guardado de sesión."""

    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True)
    last_activity = models.DateTimeField()
