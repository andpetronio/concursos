"""Regresión de UX: botón del borrador junto a cada título, sin alterar su formulario."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from .registry import TIPOS


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BotonGeneracionCercaDelTituloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="ux_borradores", password=PASSWORD,
        )
        cls.usuario.user_permissions.set(Permission.objects.filter(
            content_type__app_label__in=["concursos", "documentos"],
        ))
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.usuario)

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def test_cada_documento_tiene_boton_generico_antes_de_requisitos(self):
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        cards = html.split('<article class="document-generation-row">')[1:]
        self.assertEqual(len(cards), len(TIPOS))
        for card in cards:
            card = card.split('</article>', 1)[0]
            with self.subTest(nombre=card.split("<h4>", 1)[-1].split("</h4>", 1)[0]):
                titulo = card.index("<h4>")
                boton = card.index(">Generar borrador</button>")
                self.assertGreater(boton, titulo)
                if 'class="document-generation-missing"' in card:
                    self.assertLess(boton, card.index('class="document-generation-missing"'))
                self.assertNotIn('>Generar borrador DOCX</button>', card)
                self.assertNotIn('>Generar seis notas (ZIP)</button>', card)
                if 'data-document-inline-form' in card:
                    inicio = card.index('<form method="post"')
                    cierre = card.index('</form>', inicio)
                    self.assertTrue(inicio < boton < cierre)
                    self.assertIn('data-document-generate-button', card)
                    self.assertIn('data-document-generation-help', card)

    def test_sin_permiso_no_se_muestra_boton(self):
        self.usuario.user_permissions.set(Permission.objects.filter(
            content_type__app_label="concursos", codename="view_concurso",
        ))
        response = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generación reservada a usuarios autorizados")
        self.assertNotContains(response, 'data-document-generate-button')
