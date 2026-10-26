"""Contratos de presentación, independientes de la generación de archivos DOCX."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from .registry import TIPOS


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DocumentosPresentacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("ui_documentos", password=PASSWORD)
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label__in=["concursos", "documentos"]))
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.usuario)

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def test_siete_tipos_agrupados_sin_cambiar_catalogo(self):
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        grupos = respuesta.context["grupos_tipos_documentos"]
        self.assertEqual([g["codigo"] for g in grupos], ["preparatorios", "convocatoria", "posteriores"])
        self.assertEqual(sum(len(g["documentos"]) for g in grupos), len(TIPOS))
        self.assertEqual({d["tipo"].codigo for g in grupos for d in g["documentos"]}, {t.codigo for t in TIPOS})
        self.assertEqual(respuesta.context["documentos_listos"], sum(d["disponible"] for d in respuesta.context["tipos_documentos"]))
        for tipo in TIPOS:
            self.assertContains(respuesta, reverse("documentos:revisar", args=[self.concurso.pk, tipo.codigo]))
        self.assertContains(respuesta, "no significa que el modelo esté aprobado")
        self.assertContains(respuesta, "Todavía no hay borradores generados.")

    def test_lector_consulta_documentos_sin_acciones_generacion(self):
        self.usuario.user_permissions.set(Permission.objects.filter(
            content_type__app_label="concursos", codename="view_concurso"))
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Oficios preparatorios")
        self.assertContains(respuesta, "Generación reservada a usuarios autorizados")
        self.assertNotContains(respuesta, 'class="button button-secondary">Revisar documento</a>')

    def test_revision_preserva_complementarios_una_vez_y_errores_visibles(self):
        for codigo in ("apunsj", "convocatoria", "jurados", "dictamen", "designacion"):
            with self.subTest(tipo=codigo):
                respuesta = self.client.get(reverse("documentos:revisar", args=[self.concurso.pk, codigo]))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'id="pendientes-heading"')
                self.assertContains(respuesta, self.concurso.expediente)
                form = respuesta.context["form"]
                for campo in form.visible_fields():
                    # Cada campo se renderiza una sola vez; incluye los grupos dinámicos de presupuesto.
                    self.assertContains(respuesta, f'name="{campo.name}"', count=1)
                if codigo == "designacion":
                    self.assertContains(respuesta, "Datos presupuestarios de la designación (21 campos)")
                    self.assertEqual(len(respuesta.context["campos_presupuesto"]), 21)
                if codigo == "jurados":
                    self.assertNotContains(respuesta, "Datos complementarios del borrador")
