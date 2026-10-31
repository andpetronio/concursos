"""F4J.1: clasificación transversal sin escrituras ni nuevos permisos."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.choices import EstadoConcurso, SituacionAdministrativa
from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from core.tablero import construir_tablero
from expedientes.models import SeguimientoDocumental
from participantes.models import Aspirante, Persona


PASSWORD = "ClaveParaTablero2026!"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TableroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="lector_tablero", password=PASSWORD)
        cls.permiso_ver = Permission.objects.get(content_type__app_label="concursos", codename="view_concurso")
        cls.permiso_estado = Permission.objects.get(content_type__app_label="concursos", codename="cambiar_estado_concurso")

    def login(self, *, ver=True, estado=False):
        permisos = []
        if ver:
            permisos.append(self.permiso_ver)
        if estado:
            permisos.append(self.permiso_estado)
        self.usuario.user_permissions.set(permisos)
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def concurso(self, n=1, **extras):
        return crear_concurso(datos={**DATOS, "expediente": f"01-{n}-2026",
                                      "denominacion": f"Cargo de prueba {n}", **extras}, usuario=self.usuario)

    def test_dashboard_sin_permiso_no_filtra_datos(self):
        concurso = self.concurso()
        self.login(ver=False)
        respuesta = self.client.get(reverse("dashboard"))
        self.assertContains(respuesta, "Solicitá los permisos")
        self.assertNotContains(respuesta, concurso.denominacion)
        self.assertNotContains(respuesta, concurso.expediente)
        self.assertNotIn("tablero", respuesta.context)

    def test_sin_concursos_tiene_estado_vacio_y_enlaces(self):
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        self.assertContains(respuesta, "Todavía no hay concursos registrados")
        self.assertContains(respuesta, "Consultar concursos")
        self.assertNotContains(respuesta, "Registrar concurso")
        self.assertEqual(respuesta.context["tablero"]["totales"]["total"], 0)

    def test_totales_incluyen_finalizados_sin_tratarlos_como_activos(self):
        self.concurso(1)
        con_dictamen = self.concurso(2)
        final = self.concurso(3)
        con_dictamen.estado = EstadoConcurso.CON_DICTAMEN
        con_dictamen.save(update_fields=["estado"])
        final.estado = EstadoConcurso.FINALIZADO
        final.save(update_fields=["estado"])
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        totales = respuesta.context["tablero"]["totales"]
        self.assertEqual(totales["total"], 3)
        self.assertEqual(totales["activos"], 2)
        self.assertEqual(totales["con_dictamen"], 1)
        self.assertEqual(totales["finalizados"], 1)
        self.assertNotContains(respuesta, final.denominacion)

    def test_etapa_registrada_define_exigibilidad_y_controles_sin_foja_no_son_completos(self):
        concurso = self.concurso()
        control = concurso.controles_documentales.get(requisito="jurado_dependencia")
        control.verificado = True
        control.save(update_fields=["verificado"])
        SeguimientoDocumental.objects.filter(concurso=concurso).update(etapa="convocatoria")
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        item = respuesta.context["tablero"]["documental"][0]
        self.assertEqual(item["pendientes_exigibles"], 8)
        self.assertEqual(item["completos"], 0)
        self.assertEqual(item["motivo"], "Completar referencia de fojas")
        self.assertEqual(item["destino"], f"{concurso.get_absolute_url()}#documental-{control.pk}")

    def test_situacion_especial_tiene_prioridad_sin_cambiar_registros(self):
        concurso = self.concurso()
        concurso.situacion = SituacionAdministrativa.SUSPENDIDO
        concurso.save(update_fields=["situacion"])
        version = concurso.version
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        item = respuesta.context["tablero"]["atencion"][0]
        self.assertEqual(item["orden"], 0)
        self.assertContains(respuesta, "Revisar situación administrativa")
        concurso.refresh_from_db()
        self.assertEqual(concurso.version, version)
        self.assertEqual(concurso.situacion, SituacionAdministrativa.SUSPENDIDO)

    def test_acta_verificada_sin_aspirantes_no_declara_desierto(self):
        concurso = self.concurso()
        control = concurso.controles_documentales.get(requisito="acta_inscriptos")
        control.verificado = True
        control.fojas = "10"
        control.save(update_fields=["verificado", "fojas"])
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        item = respuesta.context["tablero"]["atencion"][0]
        self.assertEqual(item["orden"], 1)
        self.assertIn("No se presume concurso desierto", item["detalle"])
        self.assertEqual(item["destino"], concurso.get_absolute_url() + "#aspirantes")

    def test_impugnaciones_se_revisan_sin_inferir_exclusion(self):
        concurso = self.concurso()
        persona = Persona.objects.create(nombre="Ejemplo", apellido="Prueba", dni="90001011",
                                         creado_por=self.usuario, actualizado_por=self.usuario)
        Aspirante.objects.create(concurso=concurso, persona=persona,
                                situacion=Aspirante.Situacion.IMPUGNACION_PENDIENTE,
                                creado_por=self.usuario, actualizado_por=self.usuario)
        self.login()
        item = self.client.get(reverse("dashboard")).context["tablero"]["atencion"][0]
        self.assertEqual(item["orden"], 2)
        self.assertIn("impugnación", item["detalle"])

    def test_sugerencia_convocado_usa_permisos_sin_crear_cambios(self):
        concurso = self.concurso(resolucion_convocatoria="2339/26-R")
        # Los controles exigibles están completos para dejar visible la sugerencia.
        for control in concurso.controles_documentales.all():
            if control.definicion.seccion == "preparacion":
                control.verificado = True
                control.fojas = "5" if control.definicion.requiere_foja else ""
                control.save(update_fields=["verificado", "fojas"])
        self.login()
        item = self.client.get(reverse("dashboard")).context["tablero"]["atencion"][0]
        self.assertEqual(item["orden"], 4)
        self.assertEqual(item["destino"], concurso.get_absolute_url() + "#resumen")
        self.login(ver=True, estado=True)
        item = self.client.get(reverse("dashboard")).context["tablero"]["atencion"][0]
        self.assertEqual(item["destino"], reverse("concursos:estado", args=[concurso.pk]) + "?sugerencia=convocatoria")
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)

    def test_no_n_mas_un_consultas_al_agregar_concursos(self):
        self.concurso(1)
        self.concurso(2)
        self.concurso(3)
        with self.assertNumQueries(4):
            tablero = construir_tablero()
        self.assertEqual(tablero["totales"]["total"], 3)

    def test_limite_visual_no_altera_contadores_globales(self):
        for n in range(1, 11):
            self.concurso(n)
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        tablero = respuesta.context["tablero"]
        self.assertEqual(tablero["totales"]["con_revision"], 10)
        self.assertEqual(len(tablero["documental"]), 8)
        self.assertEqual(tablero["otras_documental"], 2)
        self.assertContains(respuesta, "Se muestran 8 concursos")

    def test_cabecera_unica_y_secciones_diferenciadas(self):
        self.concurso()
        self.login()
        respuesta = self.client.get(reverse("dashboard"))
        self.assertContains(respuesta, "Gestión de concursos", count=1)
        self.assertNotContains(respuesta, "Panel general")
        self.assertNotContains(respuesta, "Concursos para revisar")
        self.assertContains(respuesta, 'id="f4j-atencion-title"')
        self.assertContains(respuesta, 'id="f4j-documental-title"')
        self.assertContains(respuesta, "Cómo interpretar el tablero", count=1)
        self.assertContains(respuesta, 'class="card f4j-help"', count=1)

    def test_concurso_nuevo_es_seguimiento_no_alerta_administrativa(self):
        concurso = self.concurso()
        tablero = construir_tablero()
        self.assertEqual(tablero["totales"]["atencion_administrativa"], 0)
        self.assertEqual(tablero["totales"]["seguimiento_documental"], 1)
        self.assertEqual(tablero["documental"][0]["pk"], concurso.pk)
        self.assertEqual(tablero["documental"][0]["pendientes_exigibles"], 5)

    def test_19_de_21_controles_con_etapa_registrada_atrasada_muestra_atencion_futura(self):
        concurso = self.concurso()
        for control in concurso.controles_documentales.all():
            if control.requisito not in ("aprobacion_dictamen", "designacion"):
                control.verificado = True
                control.fojas = "15" if control.definicion.requiere_foja else ""
                control.save(update_fields=["verificado", "fojas"])
        # El caso 19/21 tiene un acta de inscriptos verificada y dos
        # aspirantes registrados. Sin ellos corresponde atención administrativa.
        for numero in (1, 2):
            persona = Persona.objects.create(
                nombre=f"Ejemplo {numero}", apellido="Aspirante",
                dni=f"9000102{numero}",
                creado_por=self.usuario, actualizado_por=self.usuario,
            )
            Aspirante.objects.create(
                concurso=concurso, persona=persona,
                creado_por=self.usuario, actualizado_por=self.usuario,
            )
        SeguimientoDocumental.objects.filter(concurso=concurso).update(etapa="convocatoria")
        concurso.estado = EstadoConcurso.CON_DICTAMEN
        concurso.save(update_fields=["estado"])

        tablero = construir_tablero()
        self.assertEqual(tablero["totales"]["atencion_administrativa"], 0)
        self.assertEqual(tablero["totales"]["seguimiento_documental"], 1)
        self.assertEqual(len(tablero["sin_revision"]), 0)
        item = tablero["documental"][0]
        self.assertEqual(item["aspirantes"], 2)
        self.assertEqual(item["completos"], 19)
        self.assertEqual(item["pendientes_exigibles"], 0)
        self.assertEqual(item["pendientes_foco"], 2)
        self.assertTrue(item["atencion_diferente"])
        self.assertEqual(item["etapa"], "Convocatoria")
        self.assertEqual(item["etapa_atencion"], "Dictamen y finalización")
        self.assertIn("Todavía no es exigible", item["detalle"])

    def test_etapa_futura_sin_actividad_no_produce_falsa_alerta(self):
        concurso = self.concurso()
        for control in concurso.controles_documentales.all():
            if control.definicion.seccion == "preparacion":
                control.verificado = True
                control.fojas = "5" if control.definicion.requiere_foja else ""
                control.save(update_fields=["verificado", "fojas"])
        tablero = construir_tablero()
        self.assertEqual(tablero["totales"]["seguimiento_documental"], 0)
        self.assertEqual(tablero["totales"]["atencion_administrativa"], 0)
        self.assertEqual(tablero["sin_revision"][0]["pk"], concurso.pk)

    def test_verificado_sin_foja_en_etapa_posterior_abre_seguimiento(self):
        concurso = self.concurso()
        for control in concurso.controles_documentales.all():
            if control.definicion.seccion == "preparacion":
                control.verificado = True
                control.fojas = "5" if control.definicion.requiere_foja else ""
                control.save(update_fields=["verificado", "fojas"])
        control = concurso.controles_documentales.get(requisito="dictamen")
        control.verificado = True
        control.save(update_fields=["verificado"])
        tablero = construir_tablero()
        item = tablero["documental"][0]
        self.assertEqual(item["motivo"], "Completar referencia de fojas")
        self.assertEqual(item["pendientes_exigibles"], 0)
        self.assertEqual(item["etapa_atencion"], "Dictamen y finalización")
        self.assertEqual(item["destino"], concurso.get_absolute_url() + f"#documental-{control.pk}")

    def test_aviso_estado_no_desaparece_por_pendiente_documental(self):
        concurso = self.concurso(resolucion_convocatoria="2339/26-R")
        item = construir_tablero()["documental"][0]
        self.assertIsNotNone(item["aviso_estado"])
        self.assertIn("convocatoria oficial", item["aviso_estado"]["texto"])
        self.assertEqual(item["aviso_estado"]["url"], concurso.get_absolute_url() + "#resumen")
        self.assertEqual(construir_tablero(puede_cambiar_estado=True)["documental"][0]["aviso_estado"]["url"],
                         reverse("concursos:estado", args=[concurso.pk]) + "?sugerencia=convocatoria")
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)

    def test_grupos_son_excluyentes_y_contadores_consistentes(self):
        simple = self.concurso(1)
        especial = self.concurso(2)
        especial.situacion = SituacionAdministrativa.SUSPENDIDO
        especial.save(update_fields=["situacion"])
        tablero = construir_tablero()
        ids = [i["pk"] for grupo in ("atencion", "documental", "sin_revision")
               for i in tablero[grupo]]
        self.assertCountEqual(ids, [simple.pk, especial.pk])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(tablero["totales"]["con_revision"], 2)
        self.assertEqual(tablero["totales"]["atencion_administrativa"], 1)
        self.assertEqual(tablero["totales"]["seguimiento_documental"], 1)
