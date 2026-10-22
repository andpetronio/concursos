from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("sessions", "0001_initial")]
    operations = [migrations.CreateModel(
        name="SessionActivity",
        fields=[
            ("session", models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True, serialize=False, to="sessions.session")),
            ("last_activity", models.DateTimeField()),
        ],
    )]
