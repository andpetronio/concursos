from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from participantes.evaluaciones import cuadro_resultados, diagnostico_sin_ganador
from participantes.models import Aspirante, CambioSituacionAspirante, EvaluacionAspirante, Persona
from participantes.services import guardar_evaluacion
from participantes.situaciones import registrar_actuacion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SituacionesAspiranteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user("operador_situaciones", password=PASSWORD)
        cls.operador.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        cls.lector = get_user_model().objects.create_user("lector_situaciones", password=PASSWORD)
        cls.lector.user_permissions.add(Permission.objects.get(
            content_type__app_label="concursos", codename="view_concurso"))
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.operador)
        for n in range(2):
            persona = Persona.objects.create(apellido=f"Aspirante {n}", nombre="Persona",
                dni=f"1234567{n}", creado_por=cls.operador, actualizado_por=cls.operador)
            Aspirante.objects.create(concurso=cls.concurso, persona=persona,
                creado_por=cls.operador, actualizado_por=cls.operador)

    def setUp(self):
        self.aspirantes = list(Aspirante.objects.filter(concurso=self.concurso).order_by("pk"))
        self.a = self.aspirantes[0]
        self.url = reverse("concursos:aspirante_situacion", args=[self.concurso.pk, self.a.pk])

    def datos(self, tipo="no_habilitacion", **extra):
        return {"tipo": tipo, "fecha_decision": "2026-10-30", "clase_documento": "acta",
                "documento": "Acta de valoración de antecedentes", "fojas": "125/127",
                "fundamento": "No cumple los requisitos mínimos que constan en el acta.",
                "version_esperada": self.a.version, **extra}

    def registrar(self, tipo="no_habilitacion", **extra):
        d = self.datos(tipo, **extra)
        return registrar_actuacion(aspirante=self.a, usuario=self.operador,
             tipo=d["tipo"], fecha_decision=date.fromisoformat(d["fecha_decision"]),
             clase_documento=d["clase_documento"], documento=d["documento"],
             fojas=d["fojas"], fundamento=d["fundamento"], version_esperada=d["version_esperada"])

    def test_no_habilitacion_conserva_inscripcion_e_historial(self):
        evento = self.registrar()
        self.a.refresh_from_db()
        self.assertEqual(self.a.situacion, "no_habilitado")
        self.assertFalse(self.a.puede_rendir)
        self.assertEqual(self.a.version, 2)
        self.assertEqual((evento.anterior, evento.nueva), ("inscripto", "no_habilitado"))
        self.assertEqual(evento.usuario, self.operador)
        self.assertEqual(evento.fojas, "125/127")
        self.assertEqual(self.concurso.aspirantes.count(), 2)
        self.assertEqual(CambioSituacionAspirante.objects.count(), 1)

    def test_exclusion_exige_resolucion_y_no_habilitacion_acta(self):
        with self.assertRaisesMessage(ValidationError, "resolución"):
            self.registrar("exclusion")
        with self.assertRaisesMessage(ValidationError, "acta"):
            self.registrar("no_habilitacion", clase_documento="resolucion")
        self.assertEqual(CambioSituacionAspirante.objects.count(), 0)

    def test_evaluacion_bloqueada_orden_no_considera_excluido_y_no_hay_ceros_ficticios(self):
        guardar_evaluacion(aspirante=self.a, antecedentes=Decimal("34"), oposicion=Decimal("51"),
             usuario=self.operador, version_esperada=0)
        self.registrar()
        cuadro = cuadro_resultados(self.concurso)
        self.assertEqual(cuadro["orden_merito"], [])
        self.assertEqual(len(cuadro["evaluaciones_pendientes"]), 1)
        self.assertEqual(len(cuadro["sin_continuidad"]), 1)
        self.assertEqual(EvaluacionAspirante.objects.count(), 1)  # histórico intacto
        with self.assertRaisesMessage(ValidationError, "no está habilitado"):
            guardar_evaluacion(aspirante=self.a, antecedentes=Decimal("10"), oposicion=Decimal("10"),
                 usuario=self.operador, version_esperada=1, motivo="Corrección")

    def test_rectificacion_restituye_evaluacion_sin_borrar_historia(self):
        self.registrar()
        self.a.refresh_from_db()
        self.registrar("rectificacion", clase_documento="resolucion", documento="Resolución aclaratoria",
                       version_esperada=2)
        self.a.refresh_from_db()
        self.assertEqual(self.a.situacion, "inscripto")
        self.assertTrue(self.a.puede_rendir)
        self.assertEqual(list(self.a.historial_situacion.values_list("nueva", flat=True)),
                         ["inscripto", "no_habilitado"])
        self.assertEqual(len(cuadro_resultados(self.concurso)["evaluaciones_pendientes"]), 2)

    def test_version_y_permisos_protegen_registro(self):
        self.registrar()
        with self.assertRaisesMessage(ValidationError, "Otro operador"):
            self.registrar("rectificacion", version_esperada=1)
        with self.assertRaises(PermissionDenied):
            registrar_actuacion(aspirante=self.a, usuario=self.lector, tipo="rectificacion",
                fecha_decision=date(2026, 10, 30), clase_documento="resolucion",
                documento="Resolución", fojas="128", fundamento="Reconsideración", version_esperada=2)
        self.assertEqual(CambioSituacionAspirante.objects.count(), 1)

    def test_impugnacion_pendiente_no_presume_exclusion(self):
        self.registrar("impugnacion", clase_documento="nota", documento="Presentación formal")
        self.a.refresh_from_db()
        self.assertTrue(self.a.puede_rendir)
        self.assertEqual(cuadro_resultados(self.concurso)["cantidad_habilitados"], 2)

    def test_nadie_habilitado_no_es_fracasado_por_merito(self):
        self.registrar()
        registrar_actuacion(aspirante=self.aspirantes[1], usuario=self.operador,
            tipo="no_habilitacion", fecha_decision=date(2026, 10, 30), clase_documento="acta",
            documento="Acta", fojas="127", fundamento="Requisitos", version_esperada=1)
        self.assertIsNone(diagnostico_sin_ganador(self.concurso))
        self.assertEqual(cuadro_resultados(self.concurso)["evaluaciones_pendientes"], [])

    def test_pantalla_lectura_y_formulario_permiso(self):
        self.client.post(reverse("login"), {"username": self.lector.username, "password": PASSWORD})
        self.assertNotContains(self.client.get(self.url), "Registrar actuación documentada")
        self.assertEqual(self.client.post(self.url, self.datos()).status_code, 403)
        self.client.logout()
        self.client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD})
        self.assertContains(self.client.get(self.url), "Registrar actuación documentada")
        self.assertEqual(self.client.post(self.url, self.datos()).status_code, 302)
        self.assertContains(self.client.get(self.url), "125/127")
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "No habilitado para oposición")

    def test_situacion_presenta_resumen_e_historial_legible(self):
        self.registrar()
        self.client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD})
        response = self.client.get(self.url)
        self.assertContains(response, "Situación vigente")
        self.assertContains(response, "Historial de situación")
        self.assertContains(response, "aspirant-situation-timeline")
        self.assertContains(response, "Registrar una rectificación")
        self.assertEqual(response.context["form"]["tipo"].value(), "rectificacion")
        self.assertIn("respalda la rectificación", response.context["form"]["clase_documento"].help_text)
        self.assertContains(response, "Registrado en SiCon el")
        self.assertNotContains(response, "<table", html=False)

    def test_fojas_incorrectas_no_guardan_y_documento_no_corresponde(self):
        self.client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD})
        self.assertContains(self.client.post(self.url, self.datos(fojas="127/125")), "inicio no puede superar")
        self.assertContains(self.client.post(self.url, self.datos(tipo="exclusion")), "resolución de la autoridad")
        self.assertEqual(CambioSituacionAspirante.objects.count(), 0)

    def test_aspirante_de_otro_concurso_no_se_accede(self):
        otro = crear_concurso(datos={**DATOS, "expediente": "01-999-2026"}, usuario=self.operador)
        self.client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD})
        self.assertEqual(self.client.get(reverse("concursos:aspirante_situacion", args=[otro.pk, self.a.pk])).status_code, 404)

    def test_sorteo_solo_ofrece_aspirantes_que_pueden_continuar(self):
        from documentos.forms import GeneracionForm
        from documentos.registry import POR_CODIGO
        self.registrar()
        form = GeneracionForm(tipo=POR_CODIGO["sorteo_acta"], concurso=self.concurso)
        ids = {valor for valor, _ in form.fields["aspirantes_presentes"].choices}
        self.assertNotIn(str(self.a.pk), ids)
        self.assertIn(str(self.aspirantes[1].pk), ids)

    def test_documento_y_fojas_se_validan_tambien_en_servicio(self):
        with self.assertRaises(ValidationError):
            self.registrar(fojas="123/122")
        with self.assertRaises(ValidationError):
            self.registrar(documento="   ")
        self.a.refresh_from_db()
        self.assertEqual(self.a.situacion, "inscripto")
        self.assertEqual(self.a.version, 1)
        self.assertFalse(CambioSituacionAspirante.objects.exists())

    def test_no_puede_levantar_restriccion_con_actuacion_distinta_de_rectificacion(self):
        self.registrar()
        self.a.refresh_from_db()
        with self.assertRaisesMessage(ValidationError, "registrá primero la rectificación"):
            self.registrar("impugnacion", clase_documento="nota", version_esperada=2)
        self.a.refresh_from_db()
        self.assertEqual(self.a.situacion, "no_habilitado")
        self.assertEqual(self.a.historial_situacion.count(), 1)
