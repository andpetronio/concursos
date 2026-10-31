"""Regresión del panel de seguimiento F4I: información, nunca acciones de escritura."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from concursos import services
from concursos.tests.test_concursos import DATOS


class SeguimientoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="operador_panel", password="prueba")
        cls.usuario.user_permissions.add(Permission.objects.get(
            content_type__app_label="concursos", codename="view_concurso"))

    def setUp(self):
        self.concurso = services.crear_concurso(datos=DATOS, usuario=self.usuario)
        # El middleware de inactividad exige un SessionActivity que solo crea
        # LoginView. force_login() lo omite y todas las visitas devuelven 302.
        respuesta = self.client.post(reverse("login"), {
            "username": self.usuario.username,
            "password": "prueba",
        })
        self.assertRedirects(respuesta, reverse("dashboard"), fetch_redirect_response=False)

    def test_resumen_reutiliza_catalogo_y_no_modifica_estado(self):
        antes = self.concurso.version
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(len(panel["etapas"]), 5)
        self.assertEqual(panel["total"], 21)
        self.assertEqual(panel["completos"], 0)
        self.assertEqual(panel["etapas"][0]["codigo"], "preparacion")
        self.assertTrue(panel["etapas"][0]["actual"])
        self.assertTrue(panel["etapas"][1]["futura"])
        self.assertContains(respuesta, "Así está el expediente")
        self.assertContains(respuesta, "Próximas revisiones documentales")
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.version, antes)
        self.assertEqual(self.concurso.estado, "preparacion")

    def test_resumen_integrado_tiene_una_sola_lista_de_etapas_y_prioridad(self):
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(respuesta, 'class="overview-columns"')
        self.assertContains(respuesta, 'class="overview-header-top"')
        self.assertContains(respuesta, 'class="overview-stage-list"', count=1)
        self.assertNotContains(respuesta, "Enlace a esta etapa")
        self.assertContains(respuesta, 'id="seguimiento-etapa-', count=5)
        self.assertContains(respuesta, 'class="overview-priority"', count=1)
        self.assertNotContains(respuesta, 'class="followup-stages"')
        self.assertNotContains(respuesta, 'class="followup-stage-inspector"')
        self.assertContains(respuesta, "Estado administrativo")
        self.assertContains(respuesta, "Situación administrativa")
        self.assertContains(respuesta, "Etapa documental")

    def test_pendientes_futuros_se_muestran_por_nombre_sin_declararlos_exigibles(self):
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["pendientes_futuros"], 16)
        self.assertEqual(len(panel["primeros_futuros"]), 3)
        self.assertEqual(panel["otros_futuros"], 13)
        self.assertContains(respuesta, "Pendientes futuros, no exigibles todavía:")
        self.assertContains(respuesta, panel["primeros_futuros"][0]["nombre"])
        self.assertContains(respuesta, 'id="seguimiento-etapa-finalizacion"')

    def test_control_con_fojas_pendientes_se_enlaza_sin_declararlo_completo(self):
        control = self.concurso.controles_documentales.get(requisito="jurado_dependencia")
        control.verificado = True
        control.save(update_fields=["verificado"])
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["completos"], 0)
        self.assertTrue(panel["primeros_pendientes"][0]["foja_pendiente"])
        self.assertContains(respuesta, f'href="#documental-{control.pk}"')
        self.assertContains(respuesta, "Foja pendiente")

    def test_documentacion_futura_no_es_exigible_en_preparacion(self):
        control = self.concurso.controles_documentales.get(requisito="designacion")
        self.assertFalse(control.completo)
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertGreater(panel["pendientes_futuros"], 0)
        self.assertTrue(all(t["seccion"] == "Preparación de convocatoria"
                            for t in panel["primeros_pendientes"]))
        self.assertNotIn(control.pk, [t["id_control"] for t in panel["primeros_pendientes"]])

    def test_acta_verificada_sin_aspirantes_sugiere_conciliar_no_desierto(self):
        control = self.concurso.controles_documentales.get(requisito="acta_inscriptos")
        control.verificado = True
        control.fojas = "125"
        control.save(update_fields=["verificado", "fojas"])
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(respuesta, "Conciliá la carga con el acta")
        self.assertNotContains(respuesta, "Concurso declarado desierto")
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, "preparacion")

    def test_etapas_permiten_consultar_controles_y_distinguen_futuros(self):
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["pendientes_futuros"], 16)
        self.assertEqual(panel["proxima_revision"]["destino"], "control")
        self.assertContains(respuesta, "Pendientes de etapas futuras")
        self.assertContains(respuesta, "Aún no exigibles")
        self.assertContains(respuesta, 'id="seguimiento-etapa-finalizacion"')
        self.assertContains(respuesta, "Sin pendientes de la etapa", count=0)
        # El enlace profundo conserva el destino del checklist original.
        control = self.concurso.controles_documentales.get(requisito="designacion")
        self.assertContains(respuesta, f'href="#documental-{control.pk}"')
        self.assertEqual(panel["etapas"][-1]["controles"][-1]["id_control"], control.pk)

    def test_foja_pendiente_tiene_prioridad_y_no_se_considera_completa(self):
        control = self.concurso.controles_documentales.get(requisito="jurado_dependencia")
        control.verificado = True
        control.save(update_fields=["verificado"])
        panel = self.client.get(self.concurso.get_absolute_url()).context["panel_seguimiento"]
        self.assertEqual(panel["proxima_revision"]["titulo"], "Completar las fojas del control")
        self.assertEqual(panel["proxima_revision"]["id_control"], control.pk)
        self.assertEqual(panel["etapas"][0]["completos"], 0)
        self.assertEqual(panel["etapas"][0]["controles"][0]["estado"], "Foja pendiente")

    def test_dictamen_registrado_en_preparacion_muestra_contraste_sin_cambiar_estado(self):
        control = self.concurso.controles_documentales.get(requisito="dictamen")
        control.verificado, control.fojas = True, "80/82"
        control.save(update_fields=["verificado", "fojas"])
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["contraste_estado"]["actual"], "Preparación")
        self.assertEqual(panel["contraste_estado"]["propuesto"], "Con dictamen")
        self.assertContains(respuesta, "Revisar coherencia entre registros")
        self.assertContains(respuesta, "El estado administrativo y la etapa documental son independientes")
        self.assertNotContains(respuesta, "Revisar propuesta de estado")  # Usuario de consulta.
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, "preparacion")
        self.assertEqual(self.concurso.historial.count(), 1)

    def test_situacion_especial_prioriza_revision_y_no_propone_transicion(self):
        self.concurso.situacion = "suspendido"
        self.concurso.save(update_fields=["situacion"])
        control = self.concurso.controles_documentales.get(requisito="dictamen")
        control.verificado, control.fojas = True, "80"
        control.save(update_fields=["verificado", "fojas"])
        panel = self.client.get(self.concurso.get_absolute_url()).context["panel_seguimiento"]
        self.assertIsNone(panel["contraste_estado"])
        self.assertEqual(panel["proxima_revision"]["destino"], "estado")
        self.assertIn("situación administrativa", panel["proxima_revision"]["titulo"])

    def test_acta_verificada_sin_carga_es_primera_revision(self):
        control = self.concurso.controles_documentales.get(requisito="acta_inscriptos")
        control.verificado, control.fojas = True, "125"
        control.save(update_fields=["verificado", "fojas"])
        panel = self.client.get(self.concurso.get_absolute_url()).context["panel_seguimiento"]
        self.assertEqual(panel["proxima_revision"]["destino"], "aspirantes")
        self.assertIn("Conciliar", panel["proxima_revision"]["titulo"])
        self.assertIsNone(panel["contraste_estado"])

    def test_atencion_abre_etapa_registrada_sin_actividad_posterior(self):
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertFalse(panel["atencion_diferente"])
        self.assertEqual(panel["etapa_atencion"], "Preparación de convocatoria")
        self.assertEqual([e["codigo"] for e in panel["etapas"] if e["en_foco"]], ["preparacion"])
        self.assertContains(respuesta, 'overview-stage--current overview-stage--focus" open')

    def test_atencion_prioriza_actuaciones_posteriores_sin_mover_etapa_registrada(self):
        from expedientes.models import SeguimientoDocumental

        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        seguimiento.etapa = "convocatoria"
        seguimiento.save(update_fields=["etapa"])
        # Caso realista: Inscripciones y Oposición completos; en Finalización
        # quedan pendientes dos resoluciones. No se cambian ni estado ni etapa.
        posteriores = self.concurso.controles_documentales.exclude(
            requisito__in=["aprobacion_dictamen", "designacion"]
        )
        for control in posteriores:
            control.verificado = True
            control.fojas = "80/82" if control.definicion.requiere_foja else ""
            control.save(update_fields=["verificado", "fojas"])
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["completos"], 19)
        self.assertEqual(panel["pendientes_futuros"], 2)
        self.assertEqual(len(panel["pendientes_exigibles"]), 0)
        self.assertEqual(panel["etapa_actual"], "Convocatoria")
        self.assertEqual(panel["etapa_atencion"], "Dictamen y finalización")
        self.assertTrue(panel["atencion_diferente"])
        self.assertEqual([e["codigo"] for e in panel["etapas"] if e["en_foco"]], ["finalizacion"])
        self.assertTrue(panel["etapas"][1]["actual"])
        self.assertFalse(panel["etapas"][1]["en_foco"])
        self.assertContains(respuesta, 'overview-stage--focus" open', count=1)
        self.assertContains(respuesta, "Controles completos · Posterior a la etapa registrada", count=2)
        self.assertContains(respuesta, "Revisar etapa registrada")
        seguimiento.refresh_from_db()
        self.assertEqual(seguimiento.etapa, "convocatoria")
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, "preparacion")
        self.assertEqual(self.concurso.historial.count(), 1)
        self.assertEqual(seguimiento.historial.count(), 0)

    def test_verificacion_posterior_sin_foja_abre_la_etapa_para_revisar(self):
        from expedientes.models import SeguimientoDocumental

        seguimiento = SeguimientoDocumental.objects.get(concurso=self.concurso)
        seguimiento.etapa = "convocatoria"
        seguimiento.save(update_fields=["etapa"])
        control = self.concurso.controles_documentales.get(requisito="dictamen")
        control.verificado = True  # Falta foja: no está completo.
        control.save(update_fields=["verificado"])
        respuesta = self.client.get(self.concurso.get_absolute_url())
        panel = respuesta.context["panel_seguimiento"]
        self.assertEqual(panel["etapa_atencion"], "Dictamen y finalización")
        self.assertFalse(panel["etapas"][-1]["completa"])
        self.assertTrue(panel["etapas"][-1]["con_actividad"])
        self.assertEqual(panel["completos"], 0)
        # La etapa registrada es Convocatoria: 5 + 3 exigibles y
        # 13 pendientes futuros, incluido el dictamen sin foja.
        self.assertEqual(panel["etapa_actual"], "Convocatoria")
        self.assertEqual(len(panel["pendientes_exigibles"]), 8)
        self.assertEqual(panel["pendientes_futuros"], 13)
        self.assertContains(respuesta, "Actuaciones registradas · Controles futuros pendientes")
        self.assertContains(respuesta, 'overview-stage--focus" open', count=1)
