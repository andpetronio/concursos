"""Destinatario de elección de jurados del estamento, sin alterar registros existentes."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documentos", "0002_membrete_institucional"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="DestinatarioPersonal",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("tratamiento", models.CharField(max_length=4, choices=[("Sr.", "Sr."), ("Sra.", "Sra.")])),
                ("cargo", models.CharField(max_length=45, choices=[
                    ("Jefe del Departamento de Personal", "Jefe del Departamento de Personal"),
                    ("Jefa del Departamento de Personal", "Jefa del Departamento de Personal")
                ])),
                ("titulo", models.CharField(max_length=100, blank=True, verbose_name="título profesional")),
                ("nombre", models.CharField(max_length=100)),
                ("apellido", models.CharField(max_length=100)),
                ("version", models.PositiveIntegerField(default=1, editable=False)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.AddConstraint("destinatariopersonal", models.CheckConstraint(condition=models.Q(pk=1), name="personal_destinatario_unico")),
    ]
