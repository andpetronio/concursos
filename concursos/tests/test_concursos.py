from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from concursos import services
from concursos.choices import EstadoConcurso, SituacionAdministrativa
from concursos.models import CambioEstado, Concurso
from core.models import SessionActivity

START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
PASSWORD = "ClaveFicticiaParaTests-2026!"
DATOS = {
    "expediente": "EXP-PRUEBA-001", "modalidad": "Modalidad de prueba",
    "denominacion": "Auxiliar de biblioteca", "funciones": "Organizar material de prueba",
    "agrupamiento": "Agrupamiento de prueba", "categoria": "Categoría de prueba",
    "tramo": "Tramo de prueba", "codigo_presupuestario": "COD-PRUEBA-001",
    "unidad": "Unidad de prueba", "dependencia": "Dependencia de prueba",
    "cadena_jerarquica": "Unidad de prueba / Dependencia de prueba",
}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConcursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user(username="operador_ficticio", password=PASSWORD)
        cls.operador.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        cls.lector = get_user_model().objects.create_user(username="lector_ficticio", password=PASSWORD)
        cls.lector.user_permissions.add(Permission.objects.get(content_type__app_label="concursos", codename="view_concurso"))
        cls.sin_permisos = get_user_model().objects.create_user(username="sin_permisos_ficticio", password=PASSWORD)

    def setUp(self):
        self.clock = patch("django.utils.timezone.now", return_value=START)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.login(self.operador)

    def login(self, usuario, client=None):
        client = client or self.client
        client.logout()
        return client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    def concurso(self, **overrides):
        return services.crear_concurso(datos={**DATOS, **overrides}, usuario=self.operador)

    def url(self, action, concurso):
        return reverse(f"concursos:{action}", args=[concurso.pk])

    def cambio(self, concurso, **overrides):
        return self.client.post(self.url("estado", concurso), {
            "estado": EstadoConcurso.CONVOCADO, "situacion": SituacionAdministrativa.NORMAL,
            "justificacion": "", "version_esperada": concurso.version, **overrides,
        })

    def test_alta_inicial_auditada_e_ignora_campos_no_editables(self):
        response = self.client.post(reverse("concursos:crear"), {
            **DATOS, "estado": EstadoConcurso.FINALIZADO, "situacion": SituacionAdministrativa.SUSPENDIDO,
            "creado_por": self.lector.pk, "actualizado_por": self.lector.pk,
        })
        concurso = Concurso.objects.get()
        self.assertRedirects(response, concurso.get_absolute_url())
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.situacion, SituacionAdministrativa.NORMAL)
        self.assertEqual(concurso.creado_por, self.operador)
        self.assertEqual(concurso.actualizado_por, self.operador)
        alta = concurso.historial.get()
        self.assertEqual(alta.usuario, self.operador)
        self.assertEqual(alta.fecha, START)
        self.assertEqual((alta.estado_anterior, alta.estado_nuevo), ("", EstadoConcurso.PREPARACION))
        self.assertEqual((alta.situacion_anterior, alta.situacion_nueva), ("", SituacionAdministrativa.NORMAL))

    def test_expedientes_repetidos_y_texto_libre_sin_catalogos(self):
        primero = self.concurso()
        response = self.client.post(reverse("concursos:crear"), DATOS)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Concurso.objects.filter(expediente=primero.expediente).count(), 2)

    def test_datos_minimos_obligatorios_y_espacios_rechazados(self):
        response = self.client.post(reverse("concursos:crear"), {campo: "  " for campo in DATOS})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), set(DATOS))
        self.assertEqual(Concurso.objects.count(), 0)
        self.assertContains(response, 'aria-describedby="id_expediente_error"')
        self.assertContains(response, 'id="id_expediente_error"', count=1)

    def test_longitud_invalida_no_guarda_y_conserva_entrada(self):
        response = self.client.post(reverse("concursos:crear"), {**DATOS, "expediente": "X" * 101})
        self.assertIn("expediente", response.context["form"].errors)
        self.assertContains(response, DATOS["denominacion"])
        self.assertEqual(Concurso.objects.count(), 0)

    def test_edicion_actualiza_responsable_sin_cambiar_estados(self):
        concurso = self.concurso()
        self.now.return_value = START + timedelta(seconds=100)
        response = self.client.post(self.url("editar", concurso), {
            **DATOS, "denominacion": "Cargo corregido", "version_esperada": concurso.version,
            "estado": EstadoConcurso.FINALIZADO, "situacion": SituacionAdministrativa.IMPUGNADO,
        })
        self.assertEqual(response.status_code, 302)
        concurso.refresh_from_db()
        self.assertEqual(concurso.denominacion, "Cargo corregido")
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.situacion, SituacionAdministrativa.NORMAL)
        self.assertEqual(concurso.actualizado_en, START + timedelta(seconds=100))
        self.assertEqual(concurso.version, 2)
        self.assertEqual(concurso.historial.count(), 1)

    def test_edicion_no_afecta_fotografia_de_otro_concurso(self):
        primero, segundo = self.concurso(), self.concurso()
        self.client.post(self.url("editar", primero), {
            **DATOS, "unidad": "Otra unidad", "dependencia": "Otra dependencia", "version_esperada": 1,
        })
        segundo.refresh_from_db()
        self.assertEqual(segundo.unidad, DATOS["unidad"])
        self.assertEqual(segundo.dependencia, DATOS["dependencia"])

    def test_cambio_manual_guarda_estado_situacion_autor_y_fecha(self):
        concurso = self.concurso()
        self.now.return_value = START + timedelta(seconds=100)
        response = self.cambio(concurso, situacion=SituacionAdministrativa.IMPUGNADO, justificacion="Motivo de prueba")
        self.assertRedirects(response, concurso.get_absolute_url())
        concurso.refresh_from_db()
        cambio = concurso.historial.first()
        self.assertEqual(concurso.estado, EstadoConcurso.CONVOCADO)
        self.assertEqual(concurso.situacion, SituacionAdministrativa.IMPUGNADO)
        self.assertEqual(cambio.estado_anterior, EstadoConcurso.PREPARACION)
        self.assertEqual(cambio.estado_nuevo, EstadoConcurso.CONVOCADO)
        self.assertEqual(cambio.situacion_anterior, SituacionAdministrativa.NORMAL)
        self.assertEqual(cambio.situacion_nueva, SituacionAdministrativa.IMPUGNADO)
        self.assertEqual(cambio.justificacion, "Motivo de prueba")
        self.assertEqual(cambio.usuario, self.operador)
        self.assertEqual(cambio.fecha, START + timedelta(seconds=100))

    def test_situacion_independiente_y_retorno_manual_a_preparacion(self):
        concurso = self.concurso()
        self.cambio(concurso, estado=EstadoConcurso.PREPARACION, situacion=SituacionAdministrativa.SUSPENDIDO)
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.situacion, SituacionAdministrativa.SUSPENDIDO)
        self.cambio(concurso, estado=EstadoConcurso.FINALIZADO)
        concurso.refresh_from_db()
        self.cambio(concurso, estado=EstadoConcurso.PREPARACION)
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.historial.count(), 4)

    def test_todos_los_estados_principales_se_pueden_registrar_manualmente(self):
        concurso = self.concurso()
        for estado in EstadoConcurso.values[1:]:
            self.assertEqual(self.cambio(concurso, estado=estado).status_code, 302)
            concurso.refresh_from_db()
            self.assertEqual(concurso.estado, estado)
        self.assertEqual(concurso.historial.count(), 5)

    def test_cambio_sin_diferencias_no_genera_historial(self):
        concurso = self.concurso()
        response = self.cambio(concurso, estado=concurso.estado)
        self.assertContains(response, "Elegí un estado o una situación diferente")
        self.assertEqual(concurso.historial.count(), 1)
        concurso.refresh_from_db()
        self.assertEqual(concurso.version, 1)

    def test_estado_situacion_y_justificacion_invalidos_no_modifican(self):
        concurso = self.concurso()
        for cambios in ({"estado": "inexistente"}, {"situacion": "inexistente"}, {"justificacion": "X" * 2001}):
            with self.subTest(cambios=cambios):
                response = self.cambio(concurso, **cambios)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.historial.count(), 1)

    def test_formulario_de_estado_get_no_modifica(self):
        concurso = self.concurso()
        self.assertEqual(self.client.get(self.url("estado", concurso)).status_code, 200)
        self.assertEqual(concurso.historial.count(), 1)

    def test_edicion_vieja_no_sobrescribe_cambio_de_estado(self):
        concurso = self.concurso()
        self.cambio(concurso)
        response = self.client.post(self.url("editar", concurso), {
            **DATOS, "denominacion": "No guardar", "version_esperada": 1,
        })
        self.assertContains(response, "Otro operador modificó el concurso")
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.CONVOCADO)
        self.assertEqual(concurso.denominacion, DATOS["denominacion"])

    def test_reenvio_de_estado_viejo_no_duplica_historial(self):
        concurso = self.concurso()
        self.cambio(concurso)
        response = self.cambio(concurso, estado=EstadoConcurso.EN_CURSO)
        self.assertContains(response, "Otro operador modificó el concurso")
        self.assertEqual(concurso.historial.count(), 2)

    def test_version_faltante_no_omite_control_de_edicion(self):
        concurso = self.concurso()
        response = self.client.post(self.url("editar", concurso), DATOS)
        self.assertIn("version_esperada", response.context["form"].errors)
        concurso.refresh_from_db()
        self.assertEqual(concurso.version, 1)

    def test_alta_es_atomica_si_falla_auditoria(self):
        with patch("concursos.services.CambioEstado.objects.create", side_effect=RuntimeError("Fallo simulado")):
            with self.assertRaises(RuntimeError):
                self.concurso()
        self.assertEqual(Concurso.objects.count(), 0)

    def test_cambio_es_atomico_si_falla_guardado_historial(self):
        concurso = self.concurso()
        with patch("concursos.services.CambioEstado.save", side_effect=RuntimeError("Fallo simulado")):
            with self.assertRaises(RuntimeError):
                services.cambiar_estado(pk=concurso.pk, estado=EstadoConcurso.CONVOCADO,
                                         situacion=SituacionAdministrativa.NORMAL, justificacion="",
                                         usuario=self.operador, version_esperada=1)
        concurso.refresh_from_db()
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)
        self.assertEqual(concurso.version, 1)
        self.assertEqual(concurso.historial.count(), 1)

    def test_busqueda_por_expediente_cargo_funciones_y_codigo(self):
        concurso = self.concurso()
        self.concurso(expediente="OTRO", denominacion="Otro cargo", funciones="Otras tareas", codigo_presupuestario="OTRO")
        for q in ("EXP-PRUEBA", "biblioteca", "material", "COD-PRUEBA"):
            with self.subTest(q=q):
                response = self.client.get(reverse("concursos:lista"), {"q": q.lower()})
                self.assertEqual([c.pk for c in response.context["concursos"]], [concurso.pk])

    def test_busqueda_y_filtro_estado_combinados(self):
        concurso = self.concurso()
        self.concurso()
        self.cambio(concurso)
        response = self.client.get(reverse("concursos:lista"), {"q": "biblioteca", "estado": "convocado"})
        self.assertEqual([c.pk for c in response.context["concursos"]], [concurso.pk])

    def test_filtros_invalidos_muestran_error_y_no_resultados(self):
        self.concurso()
        for params in ({"estado": "inexistente"}, {"q": "X" * 201}):
            response = self.client.get(reverse("concursos:lista"), params)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["filtros"].errors)
            self.assertEqual(list(response.context["concursos"]), [])

    def test_estados_vacios_del_listado(self):
        self.assertContains(self.client.get(reverse("concursos:lista")), "No hay concursos para mostrar")
        self.concurso()
        response = self.client.get(reverse("concursos:lista"), {"q": "sin coincidencia"})
        self.assertContains(response, "No hay concursos para mostrar")

    def test_paginacion_conserva_busqueda_y_filtro(self):
        for _ in range(21):
            self.concurso()
        response = self.client.get(reverse("concursos:lista"), {"q": "biblioteca", "estado": "preparacion"})
        self.assertEqual(len(response.context["concursos"]), 20)
        self.assertContains(response, 'href="?q=biblioteca&amp;estado=preparacion&amp;page=2"')
        response = self.client.get(reverse("concursos:lista"), {"q": "biblioteca", "estado": "preparacion", "page": 2})
        self.assertEqual(len(response.context["concursos"]), 1)

    def test_ficha_muestra_historial_y_escapa_texto(self):
        concurso = self.concurso(denominacion="<script>prueba</script>")
        self.cambio(concurso, justificacion="<script>motivo</script>")
        response = self.client.get(concurso.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;prueba&lt;/script&gt;")
        self.assertContains(response, "&lt;script&gt;motivo&lt;/script&gt;")
        self.assertNotContains(response, "<script>prueba</script>")
        self.assertContains(response, self.operador.username)
        self.assertContains(response, "Participantes · No disponible")
        self.assertNotContains(response, 'href="#"')

    def test_anonimos_y_usuarios_sin_permisos_no_acceden(self):
        concurso = self.concurso()
        urls = [reverse("concursos:lista"), reverse("concursos:crear"), *[self.url(a, concurso) for a in ("detalle", "editar", "estado")]]
        anonimo = Client()
        for url in urls:
            self.assertEqual(anonimo.get(url).status_code, 302)
            self.assertEqual(anonimo.post(url, DATOS).status_code, 302)
        self.login(self.sin_permisos)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, DATOS).status_code, 403)

    def test_lector_no_puede_escribir_ni_ver_acciones_de_escritura(self):
        concurso = self.concurso()
        self.login(self.lector)
        response = self.client.get(concurso.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Editar datos<")
        self.assertNotContains(response, ">Cambiar estado o situación<")
        for url in (reverse("concursos:crear"), self.url("editar", concurso), self.url("estado", concurso)):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, DATOS).status_code, 403)
        self.assertEqual(Concurso.objects.count(), 1)

    def test_permiso_editar_datos_no_autoriza_cambio_de_estado(self):
        concurso = self.concurso()
        self.lector.user_permissions.add(Permission.objects.get(content_type__app_label="concursos", codename="change_concurso"))
        self.login(self.lector)
        response = self.client.post(self.url("editar", concurso), {**DATOS, "unidad": "Cambio autorizado", "version_esperada": 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.cambio(concurso).status_code, 403)
        concurso.refresh_from_db()
        self.assertEqual(concurso.actualizado_por, self.lector)
        self.assertEqual(concurso.estado, EstadoConcurso.PREPARACION)

    def test_permiso_estados_no_autoriza_editar_datos(self):
        concurso = self.concurso()
        self.lector.user_permissions.add(Permission.objects.get(content_type__app_label="concursos", codename="cambiar_estado_concurso"))
        self.login(self.lector)
        self.assertEqual(self.cambio(concurso).status_code, 302)
        self.assertEqual(self.client.post(self.url("editar", concurso), DATOS).status_code, 403)
        self.assertEqual(concurso.historial.first().usuario, self.lector)

    def test_identificador_inexistente_devuelve_404(self):
        for action in ("detalle", "editar", "estado"):
            self.assertEqual(self.client.get(reverse(f"concursos:{action}", args=[99999])).status_code, 404)

    def test_csrf_en_todas_las_escrituras(self):
        concurso = self.concurso()
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD, "csrfmiddlewaretoken": token})
        for url in (reverse("concursos:crear"), self.url("editar", concurso), self.url("estado", concurso)):
            self.assertEqual(client.post(url, DATOS).status_code, 403)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(reverse("concursos:crear"), {**DATOS, "csrfmiddlewaretoken": token}).status_code, 302)

    def test_sesion_vencida_bloquea_alta_edicion_y_estado(self):
        concurso = self.concurso()
        urls = (reverse("concursos:crear"), self.url("editar", concurso), self.url("estado", concurso))
        for url in urls:
            self.now.return_value = START
            self.login(self.operador)
            self.now.return_value = START + timedelta(seconds=1800)
            response = self.client.post(url, {**DATOS, "denominacion": "No guardar", "estado": "convocado", "situacion": "suspendido", "version_esperada": 1})
            self.assertEqual(response.url, "/ingresar/?expired=1")
        concurso.refresh_from_db()
        self.assertEqual(concurso.version, 1)
        self.assertEqual(Concurso.objects.count(), 1)
        self.assertEqual(concurso.historial.count(), 1)

    def test_polling_de_concursos_no_renueva_pero_navegacion_intencional_si(self):
        key = self.client.session.session_key
        self.now.return_value = START + timedelta(seconds=1799)
        self.client.get(reverse("concursos:lista"))
        self.assertEqual(SessionActivity.objects.get(session_id=key).last_activity, START)
        self.client.get(reverse("concursos:lista"), HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1", HTTP_SEC_PURPOSE="prefetch")
        self.assertEqual(SessionActivity.objects.get(session_id=key).last_activity, START)
        self.client.get(reverse("concursos:lista"), HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1")
        self.now.return_value = START + timedelta(seconds=1800)
        self.assertEqual(self.client.get(reverse("concursos:lista")).status_code, 200)
        self.now.return_value = START + timedelta(seconds=3599)
        self.assertEqual(self.client.get(reverse("concursos:lista")).status_code, 302)

    def test_no_hay_eliminacion_ni_edicion_de_historial_expuestas(self):
        concurso = self.concurso()
        self.assertEqual(self.client.delete(concurso.get_absolute_url()).status_code, 405)
        self.assertEqual(self.client.get(f"/concursos/{concurso.pk}/eliminar/").status_code, 404)
        self.assertEqual(CambioEstado._meta.default_permissions, ())
        with self.assertRaises(ProtectedError):
            concurso.delete()
        with self.assertRaises(ProtectedError):
            self.operador.delete()
