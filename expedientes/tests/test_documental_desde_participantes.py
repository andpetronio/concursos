"""La carga documental existe una sola vez y se gestiona desde la pestaña correspondiente."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos import services as concursos_services
from concursos.tests.test_concursos import DATOS, PASSWORD
from expedientes.models import ControlDocumental
from participantes.models import Jurado, Persona


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DocumentalDesdeParticipantesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user(username="participantes_doc_editor", password=PASSWORD)
        cls.editor.user_permissions.set([
            Permission.objects.get(content_type__app_label="concursos", codename="view_concurso"),
            Permission.objects.get(content_type__app_label="expedientes", codename="change_controldocumental"),
        ])
        cls.lector = get_user_model().objects.create_user(username="participantes_doc_lector", password=PASSWORD)
        cls.lector.user_permissions.add(
            Permission.objects.get(content_type__app_label="concursos", codename="view_concurso")
        )

    def setUp(self):
        self.concurso = concursos_services.crear_concurso(datos=DATOS, usuario=self.editor)
        self.login(self.editor)

    def login(self, usuario):
        self.client.logout()
        return self.client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    def control(self, codigo):
        return ControlDocumental.objects.get(concurso=self.concurso, requisito=codigo)

    def jurado(self, representacion, calidad, numero):
        persona = Persona.objects.create(
            apellido="Prueba", nombre=str(numero), dni=str(32100000 + numero),
            creado_por=self.editor, actualizado_por=self.editor,
        )
        return Jurado.objects.create(
            concurso=self.concurso, persona=persona, representacion=representacion,
            calidad=calidad, titulo="Licenciado", unidad="Unidad",
            creado_por=self.editor, actualizado_por=self.editor,
        )

    def post_fojas(self, representacion, **cambios):
        control = self.control({
            "dependencia": "jurado_dependencia",
            "rectorado": "jurado_rectorado",
            "personal": "jurado_personal",
        }[representacion])
        prefijo = f"indicacion-{representacion}-"
        return self.client.post(reverse("concursos:jurado_indicacion_fojas", args=[self.concurso.pk, representacion]), {
            prefijo + "version_esperada": control.version,
            prefijo + "fojas": " 005 / 008 ",
            **cambios,
        })

    def post_oficio(self, *, incorporado=True, version=None):
        control = self.control("oficio_apunsj")
        datos = {"oficio-apunsj-version_esperada": control.version if version is None else version}
        if incorporado:
            datos["oficio-apunsj-oficio_incorporado"] = "on"
        return self.client.post(reverse("concursos:veedor_oficio_apunsj", args=[self.concurso.pk]), datos)

    def test_checklist_consulta_cinco_controles_sin_edicion_duplicada(self):
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, "Este apartado muestra el mismo control documental.", count=5)
        for codigo in ("jurado_dependencia", "jurado_rectorado", "jurado_personal", "oficio_apunsj", "acta_inscriptos"):
            control = self.control(codigo)
            self.assertNotContains(ficha, f'name="control-{control.pk}-verificado"')
            self.assertNotContains(ficha, f'name="control-{control.pk}-fojas"')
        self.assertContains(ficha, 'name="indicacion-dependencia-fojas"')
        self.assertContains(ficha, 'name="oficio-apunsj-oficio_incorporado"')
        self.assertContains(ficha, 'name="confirmar_nomina"')
        self.assertEqual(self.concurso.controles_documentales.count(), 21)

    def test_jurado_no_se_verifica_por_carga_y_si_al_registrar_fojas_completas(self):
        self.jurado("rectorado", "titular", 1)
        control = self.control("jurado_rectorado")
        self.assertFalse(control.verificado)
        respuesta = self.post_fojas("rectorado")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "registrá el titular y el suplente")
        control.refresh_from_db()
        self.assertFalse(control.verificado)
        self.jurado("rectorado", "suplente", 2)
        self.assertFalse(self.control("jurado_rectorado").verificado)
        self.assertEqual(self.post_fojas("rectorado").status_code, 302)
        control.refresh_from_db()
        self.assertEqual(control.fojas, "5/8")
        self.assertTrue(control.completo)
        self.assertEqual(control.historial.count(), 1)
        self.assertFalse(self.control("jurado_dependencia").completo)
        self.assertFalse(self.control("jurado_personal").completo)
        self.assertEqual(self.post_fojas("rectorado", **{"indicacion-rectorado-fojas": ""}).status_code, 302)
        control.refresh_from_db()
        self.assertFalse(control.completo)
        self.assertEqual(control.historial.count(), 2)

    def test_fojas_invalidas_y_version_vieja_no_reescriben_control(self):
        self.jurado("dependencia", "titular", 11)
        self.jurado("dependencia", "suplente", 12)
        for valor in ("5/2", "abc"):
            respuesta = self.post_fojas("dependencia", **{"indicacion-dependencia-fojas": valor})
            self.assertEqual(respuesta.status_code, 200)
            self.assertContains(respuesta, "Fojas de la indicación")
            self.assertFalse(self.control("jurado_dependencia").verificado)
        self.assertEqual(self.post_fojas("dependencia").status_code, 302)
        control = self.control("jurado_dependencia")
        respuesta = self.post_fojas("dependencia", **{"indicacion-dependencia-version_esperada": 1})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Otro operador modificó")
        control.refresh_from_db()
        self.assertEqual(control.version, 2)
        self.assertEqual(control.historial.count(), 1)

    def test_oficio_se_verifica_sin_veedor_y_puede_revocarse(self):
        self.assertEqual(self.concurso.veedors.count(), 0)
        self.assertEqual(self.post_oficio().status_code, 302)
        control = self.control("oficio_apunsj")
        self.assertTrue(control.completo)
        self.assertEqual(control.fojas, "")
        self.assertEqual(control.historial.count(), 1)
        self.assertEqual(self.post_oficio(incorporado=False).status_code, 302)
        control.refresh_from_db()
        self.assertFalse(control.completo)
        self.assertEqual(control.historial.count(), 2)

    def test_lector_ve_los_controles_sin_poder_modificarlos(self):
        self.login(self.lector)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(ficha.status_code, 200)
        self.assertNotContains(ficha, 'name="indicacion-rectorado-fojas"')
        self.assertNotContains(ficha, 'name="oficio-apunsj-oficio_incorporado"')
        self.assertEqual(self.post_oficio().status_code, 403)
        self.assertEqual(self.post_fojas("dependencia").status_code, 403)
        self.assertFalse(self.control("oficio_apunsj").verificado)

    def test_rutas_de_otros_concursos_no_modifican_el_actual(self):
        otro = concursos_services.crear_concurso(datos={**DATOS, "expediente": "01-998-2026"}, usuario=self.editor)
        self.jurado("dependencia", "titular", 21)
        self.jurado("dependencia", "suplente", 22)
        otro_control = otro.controles_documentales.get(requisito="jurado_dependencia")
        respuesta = self.client.post(reverse("concursos:jurado_indicacion_fojas", args=[otro.pk, "dependencia"]), {
            "indicacion-dependencia-version_esperada": otro_control.version,
            "indicacion-dependencia-fojas": "30",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(otro.controles_documentales.get(requisito="jurado_dependencia").verificado)
        self.assertFalse(self.control("jurado_dependencia").verificado)
        self.assertEqual(self.post_oficio().status_code, 302)
        self.assertFalse(otro.controles_documentales.get(requisito="oficio_apunsj").verificado)
