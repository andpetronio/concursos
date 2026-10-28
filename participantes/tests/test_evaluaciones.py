from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos import services as concursos_services
from concursos.tests.test_concursos import DATOS, PASSWORD
from participantes.evaluaciones import cuadro_resultados, faltantes_resultados, diagnostico_sin_ganador
from participantes.models import Aspirante, CambioEvaluacion, EvaluacionAspirante, Persona
from participantes.services import guardar_evaluacion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EvaluacionTests(TestCase):
    def setUp(self):
        self.operador = get_user_model().objects.create_user("evaluador_prueba", password=PASSWORD)
        self.operador.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        self.lector = get_user_model().objects.create_user("lector_prueba", password=PASSWORD)
        self.lector.user_permissions.add(Permission.objects.get(codename="view_concurso", content_type__app_label="concursos"))
        self.concurso = concursos_services.crear_concurso(datos=DATOS, usuario=self.operador)
        for n in range(3):
            persona = Persona.objects.create(apellido=f"Apellido {n}", nombre=f"Nombre {n}",
                dni=f"1234567{n}", creado_por=self.operador, actualizado_por=self.operador)
            Aspirante.objects.create(concurso=self.concurso, persona=persona,
                creado_por=self.operador, actualizado_por=self.operador)
        self.aspirantes = list(Aspirante.objects.filter(concurso=self.concurso).order_by("pk"))

    def guardar(self, i, a, o, *, version=0, motivo=""):
        return guardar_evaluacion(aspirante=self.aspirantes[i], antecedentes=Decimal(a),
            oposicion=Decimal(o), usuario=self.operador, version_esperada=version, motivo=motivo)

    def test_reconvocatoria_sin_inscriptos_exige_acta_verificada_con_foja(self):
        for aspirante in self.aspirantes:
            aspirante.delete()
        self.assertIsNone(diagnostico_sin_ganador(self.concurso))
        acta = self.concurso.controles_documentales.get(requisito="acta_inscriptos")
        acta.verificado = True
        acta.save(update_fields=["verificado"])
        self.assertIsNone(diagnostico_sin_ganador(self.concurso))
        acta.fojas = "15"
        acta.save(update_fields=["fojas"])
        salida = diagnostico_sin_ganador(self.concurso)
        self.assertEqual(salida["codigo"], "desierto_sin_inscriptos")
        self.assertEqual(salida["siguiente_codigo"], "cerrado_general")
        self.assertEqual(self.concurso.estado, "preparacion")
        self.assertEqual(self.concurso.historial.count(), 1)

    def test_reconvocatoria_insuficiencia_solo_si_evaluaciones_completas(self):
        self.guardar(0, "10", "20")
        self.guardar(1, "12", "25")
        self.assertIsNone(diagnostico_sin_ganador(self.concurso))
        self.guardar(2, "8", "29")
        salida = diagnostico_sin_ganador(self.concurso)
        self.assertEqual(salida["codigo"], "fracasado_por_merito")
        self.assertEqual(salida["siguiente_nombre"], "Cerrado General")
        self.assertEqual(self.concurso.historial.count(), 1)
        self.assertEqual(self.concurso.aspirantes.count(), 3)

    def test_reconvocatoria_general_a_abierto_pero_no_acotado_ni_abierto(self):
        for indice in range(3):
            self.guardar(indice, "0", "1")
        for modalidad, siguiente in (("cerrado_general", "abierto"), ("abierto", None), ("acotado", None)):
            with self.subTest(modalidad=modalidad):
                self.concurso.modalidad = modalidad
                resultado = diagnostico_sin_ganador(self.concurso)
                self.assertEqual(resultado["siguiente_codigo"], siguiente)

    def test_reconvocatoria_no_aparece_si_hay_aspirante_con_minimo(self):
        self.guardar(0, "10", "32.50")
        self.guardar(1, "0", "0")
        self.guardar(2, "0", "0")
        self.assertIsNone(diagnostico_sin_ganador(self.concurso))

    def test_alerta_en_ficha_no_modifica_estado_concurso(self):
        for indice in range(3):
            self.guardar(indice, "10", "20")
        acceso = self.client.post(reverse("login"), {
            "username": self.operador.username, "password": PASSWORD,
        })
        self.assertEqual(acceso.status_code, 302)
        pagina = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(pagina, "Sin orden de mérito: insuficiencia de méritos")
        self.assertContains(pagina, "Modalidad sugerida para un nuevo llamado")
        self.assertContains(pagina, "Cerrado General")
        self.concurso.refresh_from_db()
        self.assertEqual(self.concurso.estado, "preparacion")

    def test_escala_minimo_y_orden_descendente_con_desempate_por_oposicion(self):
        self.guardar(0, "32", "48")  # 80
        self.guardar(1, "34", "46")  # 80, segunda por oposición
        self.guardar(2, "10", "32.50")  # 42.50: entra
        cuadro = cuadro_resultados(self.concurso)
        self.assertEqual([f["aspirante_id"] for f in cuadro["orden_merito"]],
                         [a.pk for a in self.aspirantes])
        self.assertEqual(cuadro["escala"]["total"], "85.00")
        self.assertEqual(cuadro["escala"]["minimo"], "42.50")
        self.assertEqual([f["puesto"] for f in cuadro["orden_merito"]], [1, 2, 3])
        self.assertFalse(faltantes_resultados(cuadro))

    def test_umbral_y_exclusion_no_se_convierten_en_puesto(self):
        self.guardar(0, "10", "32.49")
        self.guardar(1, "10", "32.50")
        self.guardar(2, "0", "0")
        cuadro = cuadro_resultados(self.concurso)
        self.assertEqual(len(cuadro["orden_merito"]), 1)
        self.assertEqual(cuadro["orden_merito"][0]["puesto"], 1)
        self.assertEqual(len(cuadro["puntaje_insuficiente"]), 2)
        self.assertEqual({f["total"] for f in cuadro["puntaje_insuficiente"]}, {"42.49", "0.00"})

    def test_empate_persistente_bloquea_merito_y_no_asigna_puestos(self):
        self.guardar(0, "20", "30")
        self.guardar(1, "20", "30")
        self.guardar(2, "10", "40")  # mismo total, supera por oposición
        cuadro = cuadro_resultados(self.concurso)
        self.assertEqual(cuadro["orden_merito"][0]["aspirante_id"], self.aspirantes[2].pk)
        self.assertTrue(cuadro["empates_pendientes"])
        self.assertTrue(any("Empate" in mensaje for mensaje in faltantes_resultados(cuadro)))

    def test_pendiente_diferente_de_cero_y_rangos_sin_perdida_de_datos(self):
        self.guardar(0, "0", "0")
        self.assertEqual(len(cuadro_resultados(self.concurso)["evaluaciones_pendientes"]), 2)
        for a, o in (("34.01", "20"), ("30", "51.01"), ("-1", "2")):
            with self.subTest(a=a, o=o), self.assertRaises(ValidationError):
                self.guardar(1, a, o)
        self.assertFalse(EvaluacionAspirante.objects.filter(aspirante=self.aspirantes[1]).exists())

    def test_correccion_versionado_auditoria_y_motivo_obligatorio(self):
        self.guardar(0, "30", "40")
        with self.assertRaisesMessage(ValidationError, "motivo"):
            self.guardar(0, "31", "40", version=1)
        with self.assertRaisesMessage(ValidationError, "Otro operador"):
            self.guardar(0, "31", "40", version=0, motivo="Corrección")
        evaluacion = self.guardar(0, "31", "40", version=1, motivo="Acta aclaratoria, fs. 90")
        self.assertEqual(evaluacion.total, Decimal("71"))
        self.assertEqual(evaluacion.version, 2)
        self.assertEqual(CambioEvaluacion.objects.filter(evaluacion=evaluacion).count(), 2)
        ultimo = evaluacion.cambios.first()
        self.assertEqual((ultimo.antecedentes_antes, ultimo.antecedentes_despues), (Decimal("30"), Decimal("31")))

    def test_permisos_y_formulario_vinculado_al_concurso(self):
        aspirante = self.aspirantes[0]
        url = reverse("concursos:aspirante_evaluacion", args=[self.concurso.pk, aspirante.pk])
        self.client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD})
        self.assertContains(self.client.get(url), "Puntaje de antecedentes")
        response = self.client.post(url, {"antecedentes": "34", "oposicion": "51", "version_esperada": "0"})
        self.assertRedirects(response, self.concurso.get_absolute_url() + "#aspirantes")
        self.assertEqual(EvaluacionAspirante.objects.get(aspirante=aspirante).total, Decimal("85"))
        self.client.logout()
        self.client.post(reverse("login"), {"username": self.lector.username, "password": PASSWORD})
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.lector.pk)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"antecedentes": 0, "oposicion": 0, "version_esperada": 1}).status_code, 403)
