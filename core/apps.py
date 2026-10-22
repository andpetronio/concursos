from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Base del sistema"


class ConcursosAdminConfig(AdminConfig):
    default_site = "core.admin.ConcursosAdminSite"
