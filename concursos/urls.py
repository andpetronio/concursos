from django.urls import path

from . import views

app_name = "concursos"
urlpatterns = [
    path("", views.ConcursoListView.as_view(), name="lista"),
    path("nuevo/", views.ConcursoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ConcursoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ConcursoUpdateView.as_view(), name="editar"),
    path("<int:pk>/estado/", views.CambioEstadoView.as_view(), name="estado"),
]
