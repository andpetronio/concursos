"""Regresión F4L.5: etiquetas administrativas y checkbox nativo compacto."""
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from participantes.jurados_services import registrar_presentacion
from participantes.models import Jurado, Persona


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ResolucionJuradoPresentacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="operador_resolucion_ui", password="ClavePruebaJurados-2026!"
        )
        cls.usuario.user_permissions.set(
            Permission.objects.filter(content_type__app_label="concursos")
        )
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.usuario)
        for indice, calidad in enumerate(("titular", "suplente")):
            persona = Persona.objects.create(
                apellido="Ejemplo", nombre=f"Jurado {calidad}",
                dni=f"3355600{indice}",
                creado_por=cls.usuario, actualizado_por=cls.usuario,
            )
            Jurado.todos.create(
                concurso=cls.concurso, persona=persona, representacion="rectorado",
                calidad=calidad, titulo="Licenciado", unidad="Rectorado",
                creado_por=cls.usuario, actualizado_por=cls.usuario,
            )

    def test_selector_legible_y_checkbox_reutiliza_componente(self):
        titular = Jurado.objects.get(concurso=self.concurso, calidad="titular")
        registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            usuario=self.usuario, version_esperada=titular.version,
            motivo="excusacion", fecha_actuacion=date(2026, 10, 30), fojas="18",
        )
        # El login real inicializa SessionActivity; force_login lo omite y
        # el middleware de inactividad redirige al usuario al formulario de acceso.
        ingreso = self.client.post(reverse("login"), {
            "username": self.usuario.username,
            "password": "ClavePruebaJurados-2026!",
        })
        self.assertRedirects(ingreso, reverse("dashboard"), fetch_redirect_response=False)
        respuesta = self.client.get(reverse(
            "concursos:jurado_resolver", args=[self.concurso.pk, titular.pk]
        ))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Seleccioná una presentación pendiente")
        self.assertContains(respuesta, "Excusación presentada el 30/10/2026 (fojas 18)")
        self.assertNotContains(respuesta, "ActuacionJurado object")
        self.assertContains(respuesta, 'class="field check-field"')
        self.assertContains(respuesta, 'name="promover_suplente"')
        self.assertContains(respuesta, 'id="id_promover_suplente_helptext"')
        self.assertContains(respuesta, "Obligatorio: la plaza titular se libera antes de la promoción.")
