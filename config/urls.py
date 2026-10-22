from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("concursos/", include("concursos.urls")),
    path("admin/", admin.site.urls),
]
