"""Cotejo explícito del acta desde Aspirantes, sin duplicar controles ni cargas."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos import services as concursos_services
from concursos.tests.test_concursos import DATOS, PASSWORD
from expedientes.models import CambioControlDocumental, ControlDocumental
from participantes.models import Aspirante, Persona


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ActaDesdeAspirantesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user(username="acta_editor", password=PASSWORD)
        cls.editor.user_permissions.set([
            Permission.objects.get(content_type__app_label="concursos", codename="view_concurso"),
            Permission.objects.get(content_type__app_label="expedientes", codename="change_controldocumental"),
        ])
        cls.lector = get_user_model().objects.create_user(username="acta_lector", password=PASSWORD)
        cls.lector.user_permissions.add(
            Permission.objects.get(content_type__app_label="concursos", codename="view_concurso")
        )

    def setUp(self):
        self.concurso = concursos_services.crear_concurso(datos=DATOS, usuario=self.editor)
        self.control = ControlDocumental.objects.get(concurso=self.concurso, requisito="acta_inscriptos")
        self.login(self.editor)

    def login(self, usuario):
        self.client.logout()
        return self.client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    @property
    def url(self):
        return reverse("concursos:acta_inscriptos_cotejar", args=[self.concurso.pk])

    def cargar(self, numero):
        persona = Persona.objects.create(
            apellido=f"Apellido {numero}", nombre=f"Nombre {numero}", dni=f"2999000{numero}",
            creado_por=self.editor, actualizado_por=self.editor,
        )
        return Aspirante.objects.create(
            concurso=self.concurso, persona=persona,
            creado_por=self.editor, actualizado_por=self.editor,
        )

    def confirmar(self, **cambios):
        self.control.refresh_from_db()
        datos = {
            "version_esperada": self.control.version,
            "cantidad_vista": self.concurso.aspirantes.count(),
            "fojas": "45 / 48",
            "confirmar_nomina": "on",
            **cambios,
        }
        return self.client.post(self.url, datos)

    def test_cargar_aspirantes_no_verifica_el_acta(self):
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, "Acta de inscriptos")
        self.assertContains(detalle, 'name="confirmar_nomina"')
        self.assertContains(detalle, 'name="fojas"')
        self.assertContains(detalle, 'name="cantidad_vista"')  # Oculto, no carga manual.
        self.assertNotContains(detalle, 'name="cantidad_cotejada"')
        self.cargar(1)
        self.cargar(2)
        self.control.refresh_from_db()
        self.assertFalse(self.control.verificado)
        self.assertEqual(self.control.version, 1)
        self.assertEqual(self.control.historial.count(), 0)

    def test_confirmar_acta_reutiliza_control_fojas_e_historial(self):
        self.cargar(1)
        self.cargar(2)
        respuesta = self.confirmar()
        self.assertRedirects(respuesta, self.concurso.get_absolute_url() + "#aspirantes")
        self.control.refresh_from_db()
        self.assertEqual(self.control.fojas, "45/48")
        self.assertEqual(self.control.cantidad_cotejada, 2)
        self.assertTrue(self.control.completo)
        self.assertEqual(self.control.version, 2)
        self.assertEqual(self.control.responsable, self.editor)
        self.assertIsNotNone(self.control.verificado_en)
        self.assertEqual(self.control.historial.get().nuevo["cantidad_cotejada"], 2)
        self.assertEqual(self.concurso.controles_documentales.count(), 21)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(ficha, "Nómina cotejada con el acta")
        self.assertContains(ficha, "45/48")
        self.assertContains(ficha, "Verificado")
        self.assertFalse(ficha.context["acta_inscriptos_revisar"])

    def test_sin_confirmacion_o_con_foja_invalida_no_guarda(self):
        for cambios in ({"confirmar_nomina": ""}, {"fojas": ""}, {"fojas": "8/5"}):
            with self.subTest(cambios=cambios):
                respuesta = self.confirmar(**cambios)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["cotejo_acta_form"].errors)
                self.control.refresh_from_db()
                self.assertFalse(self.control.verificado)
                self.assertEqual(self.control.version, 1)
        self.assertEqual(CambioControlDocumental.objects.count(), 0)

    def test_cero_inscriptos_se_confirma_explicitamente(self):
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(ficha, "Confirmo que el acta consigna cero inscriptos")
        self.assertEqual(self.confirmar(fojas="50").status_code, 302)
        self.control.refresh_from_db()
        self.assertEqual(self.control.cantidad_cotejada, 0)
        self.assertTrue(self.control.completo)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertFalse(ficha.context["acta_inscriptos_revisar"])
        self.assertFalse(ficha.context["panel_seguimiento"]["proxima_revision"]["titulo"].startswith("Conciliar el acta"))
        self.assertNotContains(ficha, "La ausencia de registros no acredita por sí sola")

    def test_nueva_inscripcion_advierte_y_no_revoca_verificacion(self):
        self.cargar(1)
        self.confirmar()
        self.cargar(2)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertTrue(ficha.context["acta_inscriptos_revisar"])
        self.assertContains(ficha, "Se modificó la cantidad de aspirantes desde el último cotejo")
        self.assertContains(ficha, "Revisar cotejo de la nómina de inscriptos")
        self.control.refresh_from_db()
        self.assertTrue(self.control.verificado)
        self.assertEqual(self.control.cantidad_cotejada, 1)
        self.assertEqual(self.confirmar().status_code, 302)
        self.control.refresh_from_db()
        self.assertEqual(self.control.cantidad_cotejada, 2)
        self.assertEqual(self.control.historial.count(), 2)

    def test_una_ficha_desactualizada_no_confirma_nuevo_cotejo(self):
        self.cargar(1)
        self.confirmar()
        self.cargar(2)
        respuesta = self.confirmar(cantidad_vista=1)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "La nómina cambió desde que abriste la ficha")
        self.control.refresh_from_db()
        self.assertEqual(self.control.cantidad_cotejada, 1)
        self.assertEqual(self.control.historial.count(), 1)

    def test_version_vieja_no_sobrescribe_control(self):
        self.cargar(1)
        self.confirmar()
        respuesta = self.confirmar(version_esperada=1)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Otro operador modificó este control")
        self.control.refresh_from_db()
        self.assertEqual(self.control.version, 2)
        self.assertEqual(self.control.historial.count(), 1)

    def test_checklist_sigue_siendo_el_mismo_control_y_no_coteja_por_si_solo(self):
        self.cargar(1)
        self.confirmar()
        self.control.refresh_from_db()
        prefijo = f"control-{self.control.pk}-"
        respuesta = self.client.post(
            reverse("concursos:control_documental", args=[self.concurso.pk, self.control.pk]),
            {prefijo + "version_esperada": self.control.version,
             prefijo + "fojas": "46/49", prefijo + "verificado": "on", prefijo + "observaciones": ""},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.control.refresh_from_db()
        self.assertTrue(self.control.completo)
        self.assertEqual(self.control.fojas, "46/49")
        self.assertIsNone(self.control.cantidad_cotejada)  # Cambió la referencia: cotejo pendiente.
        self.assertEqual(self.control.historial.count(), 2)

    def test_lector_solo_consulta_y_post_rechazado(self):
        self.login(self.lector)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(ficha.status_code, 200)
        self.assertNotContains(ficha, 'name="confirmar_nomina"')
        self.assertContains(ficha, "requiere permisos de Control documental")
        post = self.client.post(self.url, {
            "fojas": "23", "confirmar_nomina": "on", "version_esperada": 1, "cantidad_vista": 0,
        })
        self.assertEqual(post.status_code, 403)
        self.control.refresh_from_db()
        self.assertFalse(self.control.verificado)
        self.assertFalse(self.control.historial.exists())

    def test_acta_no_puede_modificarse_desde_otro_concurso(self):
        segundo = concursos_services.crear_concurso(
            datos={**DATOS, "expediente": "01-999-2026"}, usuario=self.editor,
        )
        self.cargar(1)
        self.confirmar()
        self.control.refresh_from_db()
        original = self.control.fojas
        self.assertEqual(original, "45/48")
        control_segundo = segundo.controles_documentales.get(requisito="acta_inscriptos")
        self.assertFalse(control_segundo.verificado)
        self.assertEqual(control_segundo.fojas, "")
