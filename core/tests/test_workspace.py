"""Presentation-only SDD-006 2B contracts, with an isolated pilot URLconf."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import path, reverse

from config.urls import urlpatterns as production_patterns
from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from concursos.views import ConcursoDetailView

urlpatterns = [
    path("qa/piloto/<int:pk>/", ConcursoDetailView.as_view(
        template_name="concursos/detalle_piloto.html"), name="qa_pilot"),
    *production_patterns,
]
PASSWORD = "Synthetic-Only-2026!"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkspacePresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="presentation_test", password=PASSWORD)
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.user)
        from participantes.models import Aspirante, Jurado, Persona, Veedor
        actor = {"creado_por": cls.user, "actualizado_por": cls.user}
        first = Persona.objects.create(nombre="Ana", apellido="Ejemplo", dni="90000001", **actor)
        second = Persona.objects.create(nombre="Ana", apellido="Ejemplo", dni="90000002", **actor)
        Jurado.objects.create(concurso=cls.concurso, persona=first, representacion="rectorado",
                              calidad="titular", titulo="Título de prueba", unidad="Unidad de prueba",
                              cargo="Cargo histórico", **actor)
        Veedor.objects.create(concurso=cls.concurso, persona=second, cargo="Cargo veedor", **actor)
        for person in [first, second]:
            Aspirante.objects.create(concurso=cls.concurso, persona=person, **actor)


    def login(self, *permissions):
        self.user.user_permissions.set(Permission.objects.filter(codename__in=permissions))
        self.client.post(reverse("login"), {"username": self.user.username, "password": PASSWORD})

    def test_login_identity_without_placeholder_and_independent_layout(self):
        response = self.client.get(reverse("login") + "?expired=1&next=/concursos/")
        self.assertContains(response, "SiCon")
        self.assertContains(response, "La gestión de concursos")
        self.assertNotContains(response, 'class="artwork-slot"')
        self.assertNotContains(response, "Espacio reservado para ilustración abstracta")
        self.assertContains(response, 'name="next" value="/concursos/"')
        self.assertContains(response, "Tu sesión venció por inactividad")
        self.assertNotContains(response, "navigation.js")
        self.assertNotContains(response, "primary-navigation")

    def test_dashboard_without_permissions_explains_access(self):
        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Panel inicial")
        self.assertContains(response, "Solicitá los permisos")
        self.assertNotContains(response, "Consultar concursos")
        self.assertNotContains(response, f'href="{reverse("concursos:crear")}"')

    def test_reader_has_consultation_but_not_registration(self):
        self.login("view_concurso")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Consultar concursos")
        self.assertNotContains(response, "Registrar concurso")

    def test_editor_has_existing_workflow_links(self):
        self.login("view_concurso", "add_concurso")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, f'href="{reverse("concursos:crear")}"')
        self.assertContains(response, "Control documental")
        self.assertContains(response, "no reemplaza")
        self.assertNotContains(response, "qa/piloto")

    @override_settings(ROOT_URLCONF=__name__)
    def test_pilot_reuses_real_context_and_preserves_production_detail(self):
        self.login("view_concurso")
        response = self.client.get(reverse("qa_pilot", args=[self.concurso.pk]))
        self.assertContains(response, "Propuesta visual · pendiente de aceptación")
        self.assertContains(response, 'aria-label="Secciones de la ficha"')
        for anchor in ["datos-concurso", "jurados", "veedores", "aspirantes", "control-documental", "documentos", "historial"]:
            self.assertContains(response, f'href="#{anchor}"')
        self.assertContains(response, "Preparación de convocatoria")
        self.assertContains(response, "90000001")
        self.assertContains(response, "90000002")
        self.assertContains(response, "Título de prueba")
        self.assertContains(response, "Cargo registrado anteriormente: Cargo histórico")
        self.assertContains(response, "Cargo veedor")
        self.assertContains(response, '<strong>Ejemplo, Ana</strong>', count=4)
        self.assertTemplateUsed(response, "components/person_identity.html")
        self.assertTemplateUsed(response, "participantes/tabla_piloto.html")
        self.assertNotContains(response, "Guardar etapa documental")
        self.assertNotContains(response, "Editar datos")
        self.assertTemplateUsed(response, "expedientes/checklist.html")
        self.assertTemplateUsed(response, "documentos/seccion.html")
        response = self.client.get(reverse("concursos:detalle", args=[self.concurso.pk]))
        self.assertNotContains(response, "Propuesta visual")
        self.assertTemplateUsed(response, "concursos/detalle.html")
        self.login("view_concurso", "cambiar_estado_concurso")
        response = self.client.get(reverse("qa_pilot", args=[self.concurso.pk]))
        self.assertContains(response, f'<a href="{reverse("concursos:estado", args=[self.concurso.pk])}" class="button button-secondary">Cambiar estado o situación</a>', html=True)


    def test_pilot_is_not_published_by_production_urlconf(self):
        self.login("view_concurso")
        self.assertEqual(self.client.get(f"/qa/piloto/{self.concurso.pk}/").status_code, 404)
