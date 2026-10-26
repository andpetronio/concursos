# Membrete vigente administrado por la institución; históricos DOCX inmutables.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documentos", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="MembreteInstitucional",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contenido", models.BinaryField(editable=False)),
                ("nombre_archivo", models.CharField(max_length=150)),
                ("tipo_mime", models.CharField(max_length=20)),
                ("sha256", models.CharField(editable=False, max_length=64)),
                ("version", models.PositiveIntegerField(default=1, editable=False)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.AddConstraint(
            model_name="membreteinstitucional",
            constraint=models.CheckConstraint(condition=models.Q(pk=1), name="membrete_institucional_unico"),
        ),
    ]
