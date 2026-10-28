from django.urls import path

from . import views
from participantes import views as participante_views
from expedientes import views as documental_views

app_name = "concursos"
urlpatterns = [
    path("", views.ConcursoListView.as_view(), name="lista"),
    path("nuevo/", views.ConcursoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ConcursoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ConcursoUpdateView.as_view(), name="editar"),
    path("<int:pk>/estado/", views.CambioEstadoView.as_view(), name="estado"),
    path("<int:pk>/control-documental/<int:control_id>/", documental_views.ControlDocumentalUpdateView.as_view(), name="control_documental"),
    path("<int:pk>/control-documental/<int:control_id>/historial/", documental_views.HistorialControlView.as_view(), name="control_historial"),
    path("<int:pk>/control-documental/etapa/", documental_views.EtapaDocumentalUpdateView.as_view(), name="etapa_documental"),
    path("<int:pk>/control-documental/etapa/historial/", documental_views.HistorialEtapaView.as_view(), name="etapa_historial"),
    path("<int:pk>/participantes/jurados/nuevo/", participante_views.JuradoAltaView.as_view(), name="jurado_crear"),
    path("<int:pk>/participantes/jurados/<int:participacion_id>/editar/",
         participante_views.JuradoEdicionView.as_view(), name="jurado_editar"),
    path("<int:pk>/participantes/veedores/nuevo/", participante_views.VeedorAltaView.as_view(), name="veedor_crear"),
    path("<int:pk>/participantes/veedores/<int:participacion_id>/editar/",
         participante_views.VeedorEdicionView.as_view(), name="veedor_editar"),
    path("<int:pk>/participantes/aspirantes/nuevo/", participante_views.AspiranteAltaView.as_view(), name="aspirante_crear"),
    path("<int:pk>/participantes/aspirantes/<int:participacion_id>/editar/",
         participante_views.AspiranteEdicionView.as_view(), name="aspirante_editar"),
    path("<int:pk>/participantes/aspirantes/<int:participacion_id>/evaluacion/",
         participante_views.EvaluacionAspiranteView.as_view(), name="aspirante_evaluacion"),
    path("<int:pk>/participantes/personas/<int:persona_id>/editar/",
         participante_views.PersonaEdicionView.as_view(), name="persona_editar"),
]
