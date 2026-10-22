from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.template.response import TemplateResponse


class ConcursosAdminSite(AdminSite):
    site_header = "Administración de Concursos Nodocentes"
    site_title = "Concursos · UNSJ"

    def login(self, request, extra_context=None):
        if self.has_permission(request):
            return redirect("admin:index")
        if request.user.is_authenticated:
            return TemplateResponse(request, "core/forbidden.html", status=403)
        destination = request.GET.get(REDIRECT_FIELD_NAME, reverse("admin:index"))
        # LoginView valida que next sea local antes de usarlo.
        return redirect_to_login(destination, reverse("login"))

