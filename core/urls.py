from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ingresar/", views.LoginView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("sesion/actividad/", views.activity, name="session_activity"),
    path("sesion/estado/", views.session_status, name="session_status"),
    path("health/", views.health, name="health"),
]
