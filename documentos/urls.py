from django.urls import path
from . import views

app_name = "documentos"
urlpatterns = [
    path("configuracion-institucional/", views.ConfiguracionView.as_view(), name="configuracion"),
    path("configuracion-institucional/apunsj/", views.ConfiguracionAPUNSJView.as_view(), name="configuracion_apunsj"),
    path("configuracion-institucional/personal/", views.DestinatarioPersonalView.as_view(), name="configuracion_personal"),
    path("configuracion-institucional/membrete/", views.MembreteInstitucionalView.as_view(), name="membrete"),
    path("configuracion-institucional/membrete/imagen/", views.ImagenMembreteView.as_view(), name="membrete_imagen"),
    path("<int:pk>/documentos/<slug:tipo>/revisar/", views.GeneracionView.as_view(), name="revisar"),
    path("<int:pk>/documentos/<slug:tipo>/generar/", views.GeneracionEnFichaView.as_view(), name="generar_en_ficha"),
    path("<int:pk>/documentos/archivo/<int:documento_id>/jurado/<int:indice>/", views.DescargaView.as_view(), name="descargar_jurado"),
    path("<int:pk>/documentos/archivo/<int:documento_id>/", views.DescargaView.as_view(), name="descargar"),
]
