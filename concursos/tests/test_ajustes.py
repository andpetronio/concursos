from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.forms import ConcursoForm
from concursos.models import Concurso
from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AjustesConcursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="ajustes_concurso", password=PASSWORD)
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def test_funciones_opcionales_en_alta_y_contenido_existente_en_edicion(self):
        response = self.client.post(reverse("concursos:crear"), {k: v for k, v in DATOS.items() if k != "funciones"})
        self.assertEqual(response.status_code, 302)
        concurso = Concurso.objects.get()
        self.assertEqual(concurso.funciones, "")
        original = crear_concurso(datos=DATOS, usuario=self.usuario)
        response = self.client.get(reverse("concursos:editar", args=[original.pk]))
        self.assertContains(response, 'class="card form-section additional-data" open')
        self.assertContains(response, DATOS["funciones"])
        response = self.client.post(reverse("concursos:editar", args=[original.pk]), {
            **DATOS, "denominacion": "Cambio de denominación", "version_esperada": 1,
        })
        self.assertEqual(response.status_code, 302)
        original.refresh_from_db()
        self.assertEqual(original.funciones, DATOS["funciones"])
        self.assertFalse(ConcursoForm().fields["funciones"].required)

    def test_expediente_repetido_se_guarda_con_advertencia(self):
        crear_concurso(datos=DATOS, usuario=self.usuario)
        response = self.client.post(reverse("concursos:crear"), DATOS, follow=True)
        self.assertContains(response, "El número de expediente ya está registrado en otro concurso")
        self.assertEqual(Concurso.objects.filter(expediente=DATOS["expediente"]).count(), 2)

    def test_expediente_historico_conservado_y_cambio_exige_formato(self):
        concurso = crear_concurso(datos=DATOS, usuario=self.usuario)
        Concurso.objects.filter(pk=concurso.pk).update(expediente="EXP-ANTERIOR")
        concurso.refresh_from_db()
        url = reverse("concursos:editar", args=[concurso.pk])
        self.assertEqual(self.client.post(url, {**DATOS, "expediente": "EXP-ANTERIOR", "version_esperada": 1}).status_code, 302)
        concurso.refresh_from_db()
        self.assertEqual(concurso.expediente, "EXP-ANTERIOR")
        response = self.client.post(url, {**DATOS, "expediente": "EXP-NUEVO", "version_esperada": 2})
        self.assertIn("expediente", response.context["form"].errors)
        concurso.expediente = "01-0-2026"
        with self.assertRaises(ValidationError):
            concurso.full_clean()

    def test_expediente_invalido_rechazado_sin_js_y_en_servicio(self):
        response = self.client.post(reverse("concursos:crear"), {**DATOS, "expediente": "01-0001-2026"})
        self.assertIn("expediente", response.context["form"].errors)
        with self.assertRaises(ValidationError):
            crear_concurso(datos={**DATOS, "expediente": "incorrecto"}, usuario=self.usuario)
        self.assertFalse(Concurso.objects.exists())


    def test_antecedentes_vacancia_distinguen_causa_campos_y_legacy(self):
        respuesta = self.client.get(reverse("concursos:crear"))
        self.assertContains(respuesta, 'data-vacancy-fields')
        self.assertContains(respuesta, 'data-vacancy-cessation')
        self.assertContains(respuesta, 'data-vacancy-act')
        self.assertContains(respuesta, 'data-vacancy-other')
        self.assertContains(respuesta, 'name="motivo_baja"')
        self.assertContains(respuesta, "Detalle histórico de la baja")
        self.assertContains(respuesta, "Acto administrativo de respaldo")
        self.assertIn(("traslado", "Cargo trasladado"), list(ConcursoForm().fields["causa_vacancia"].choices))

    def test_antecedentes_historicos_siguen_editables_y_no_se_borran(self):
        concurso = crear_concurso(datos={**DATOS, "motivo_baja": "Cese acreditado antiguo",
                                          "acto_vacancia": "Acto histórico 123"}, usuario=self.usuario)
        respuesta = self.client.get(reverse("concursos:editar", args=[concurso.pk]))
        self.assertContains(respuesta, "Cese acreditado antiguo")
        self.assertContains(respuesta, "Acto histórico 123")
        self.assertContains(respuesta, 'class="vacancy-legacy" open')
        respuesta = self.client.post(reverse("concursos:editar", args=[concurso.pk]), {
            **DATOS, "motivo_baja": "Cese acreditado antiguo", "acto_vacancia": "Acto histórico 123",
            "version_esperada": concurso.version,
        })
        self.assertEqual(respuesta.status_code, 302)
        concurso.refresh_from_db()
        self.assertEqual(concurso.motivo_baja, "Cese acreditado antiguo")
        self.assertEqual(concurso.acto_vacancia, "Acto histórico 123")
