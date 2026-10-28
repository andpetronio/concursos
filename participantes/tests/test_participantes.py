from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from concursos import services as concurso_services
from concursos.tests.test_concursos import DATOS
from participantes.models import Aspirante, Jurado, Persona, Veedor
from core.models import SessionActivity


START = datetime(2026, 2, 1, 12, tzinfo=timezone.utc)
PASSWORD = "ClaveFicticiaParticipantes-2026!"
PERSONA = {"apellido": "Apellido Ficticio", "nombre": "Nombre Ficticio", "dni": "12.345.678"}
JURADO = {**PERSONA, "representacion": "dependencia", "calidad": "titular",
          "titulo": "Técnico", "unidad": "Unidad de prueba", "email": "prueba@example.invalid", "telefono": "000-0000000"}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ParticipanteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user(username="operador_participantes", password=PASSWORD)
        cls.operador.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        cls.lector = get_user_model().objects.create_user(username="lector_participantes", password=PASSWORD)
        cls.lector.user_permissions.add(Permission.objects.get(content_type__app_label="concursos", codename="view_concurso"))
        cls.sin_permisos = get_user_model().objects.create_user(username="sin_permisos_participantes", password=PASSWORD)

    def setUp(self):
        self.clock = patch("django.utils.timezone.now", return_value=START)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.login(self.operador)
        self.concurso = concurso_services.crear_concurso(datos=DATOS, usuario=self.operador)

    def login(self, usuario, client=None):
        client = client or self.client
        client.logout()
        return client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    def url(self, name, concurso=None, *extra):
        return reverse(f"concursos:{name}", args=[(concurso or self.concurso).pk, *extra])

    def test_jurado_progresivo_y_plaza_unica_en_formulario_y_base(self):
        response = self.client.post(self.url("jurado_crear"), JURADO)
        self.assertRedirects(response, self.concurso.get_absolute_url() + "#jurados")
        jurado = Jurado.objects.get()
        self.assertEqual(jurado.persona.dni, "12345678")
        self.assertEqual(jurado.persona.creado_por, self.operador)
        self.assertEqual(jurado.creado_por, self.operador)
        self.assertEqual(jurado.actualizado_por, self.operador)
        self.assertEqual(jurado.creado_en, START)
        self.assertEqual(Jurado.objects.count(), 1)  # No se exigen las otras cinco plazas.
        duplicado = {**JURADO, "apellido": "Otra", "nombre": "Persona", "dni": "22.222.222"}
        response = self.client.post(self.url("jurado_crear"), duplicado)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "Ya hay un integrante del jurado registrado para esa representación y calidad en este concurso.")
        self.assertNotContains(response, "Ya existe un/a Jurado con este/a Concurso")
        self.assertEqual(Jurado.objects.count(), 1)
        self.assertEqual(Persona.objects.count(), 1)  # El alta fallida revierte la persona nueva.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Jurado.objects.create(concurso=self.concurso, persona=Persona.objects.create(
                    apellido="Otra", nombre="Persona", dni="22222222",
                    creado_por=self.operador, actualizado_por=self.operador),
                    representacion="dependencia", calidad="titular", titulo="Técnico", cargo="Agente",
                    creado_por=self.operador, actualizado_por=self.operador,
                )

    def test_jurado_requiere_seleccion_explicita_de_plaza(self):
        response = self.client.get(self.url("jurado_crear"))
        self.assertContains(response, "Seleccioná una representación")
        self.assertContains(response, "Seleccioná una calidad")
        for omitido in ("representacion", "calidad"):
            datos = {campo: valor for campo, valor in JURADO.items() if campo != omitido}
            response = self.client.post(self.url("jurado_crear"), datos)
            self.assertIn(omitido, response.context["form"].errors)
        self.assertEqual(Jurado.objects.count(), 0)

    def test_jurado_unidad_obligatoria_sin_exigir_ni_exponer_cargo(self):
        response = self.client.get(self.url("jurado_crear"))
        self.assertContains(response, 'name="unidad"')
        self.assertNotContains(response, 'name="cargo"')
        for valor in ("", "   ", "X" * 201):
            with self.subTest(unidad=valor):
                response = self.client.post(self.url("jurado_crear"), {**JURADO, "unidad": valor})
                self.assertIn("unidad", response.context["form"].errors)
        self.assertEqual(Persona.objects.count(), 0)
        response = self.client.post(self.url("jurado_crear"), JURADO)
        self.assertEqual(response.status_code, 302)
        jurado = Jurado.objects.get()
        self.assertEqual((jurado.unidad, jurado.cargo), (JURADO["unidad"], ""))
        response = self.client.get(self.url("jurado_editar", None, jurado.pk))
        self.assertContains(response, 'value="Unidad de prueba"')
        self.assertNotContains(response, 'name="cargo"')
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            **JURADO, "unidad": "", "version_esperada": 1,
        })
        self.assertIn("unidad", response.context["form"].errors)
        jurado.refresh_from_db()
        self.assertEqual((jurado.unidad, jurado.version), (JURADO["unidad"], 1))

    def test_unidad_por_participacion_conserva_cargo_anterior_y_otros_datos(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        # Estado legado sin unidad: no inferirla del cargo ni del concurso.
        Jurado.objects.filter(pk=jurado.pk).update(cargo="Cargo histórico de prueba", unidad="")
        jurado.refresh_from_db()
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, "Cargo registrado anteriormente: Cargo histórico de prueba")
        self.assertContains(detalle, "Pendiente de completar")
        otro_concurso = concurso_services.crear_concurso(datos=DATOS, usuario=self.operador)
        self.assertEqual(self.client.post(self.url("jurado_crear", otro_concurso), {
            **JURADO, "unidad": "Otra unidad de servicio",
        }).status_code, 302)
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            **JURADO, "unidad": "Unidad de servicio declarada", "version_esperada": 1,
            "cargo": "No sobrescribir el cargo histórico",
        })
        self.assertEqual(response.status_code, 302)
        jurado.refresh_from_db()
        self.assertEqual((jurado.unidad, jurado.cargo), ("Unidad de servicio declarada", "Cargo histórico de prueba"))
        self.assertEqual((jurado.titulo, jurado.email, jurado.telefono, jurado.representacion, jurado.calidad),
                         tuple(JURADO[campo] for campo in ("titulo", "email", "telefono", "representacion", "calidad")))
        otro = Jurado.objects.get(concurso=otro_concurso)
        self.assertEqual(otro.persona_id, jurado.persona_id)
        self.assertEqual(otro.unidad, "Otra unidad de servicio")
        self.assertNotEqual(jurado.unidad, self.concurso.unidad)
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, '<th scope="col">Unidad</th>', html=True)
        self.assertContains(detalle, "Unidad de servicio declarada")
        self.assertContains(detalle, "Cargo histórico de prueba")

    def test_aspirante_dni_unico_local_y_persona_reutilizada_en_otros_concursos(self):
        self.assertEqual(self.client.post(self.url("aspirante_crear"), PERSONA).status_code, 302)
        duplicado = self.client.post(self.url("aspirante_crear"), {**PERSONA, "dni": "12-345-678"})
        self.assertEqual(duplicado.status_code, 200)
        self.assertTrue(duplicado.context["form"].errors)
        segundo = concurso_services.crear_concurso(datos={**DATOS, "expediente": "01-2-2026"}, usuario=self.operador)
        self.assertEqual(self.client.post(self.url("aspirante_crear", segundo), {**PERSONA, "dni": "12345678"}).status_code, 302)
        self.assertEqual(Persona.objects.count(), 1)
        self.assertEqual(Aspirante.objects.count(), 2)
        self.assertEqual(set(Aspirante.objects.values_list("concurso_id", flat=True)), {self.concurso.pk, segundo.pk})
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Aspirante.objects.create(concurso=self.concurso, persona=Persona.objects.get(),
                                        creado_por=self.operador, actualizado_por=self.operador)

    def test_dni_invalido_y_nombre_distinto_no_sobrescriben_persona_compartida(self):
        self.client.post(self.url("aspirante_crear"), PERSONA)
        for dni in ("ABC123456", "..--", "1234567890123"):
            with self.subTest(dni=dni):
                response = self.client.post(self.url("veedor_crear"), {**PERSONA, "dni": dni})
                self.assertIn("dni", response.context["form"].errors)
        response = self.client.post(self.url("veedor_crear"), {**PERSONA, "nombre": "Nombre diferente"})
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertEqual(Persona.objects.get().nombre, PERSONA["nombre"])
        self.assertEqual(Veedor.objects.count(), 0)

    def test_veedor_apunsj_opcional_y_sin_selector_institucion(self):
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, "No hay veedores registrados. El concurso puede continuar")
        response = self.client.get(self.url("veedor_crear"))
        self.assertNotContains(response, 'name="institucion"')
        self.assertEqual(self.client.post(self.url("veedor_crear"), PERSONA).status_code, 302)
        self.assertEqual(Veedor.objects.count(), 1)
        self.assertEqual(self.concurso.historial.count(), 1)
        self.assertEqual(self.concurso.estado, "preparacion")

    def test_ficha_reutiliza_tablas_y_muestra_los_tres_tipos(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        self.client.post(self.url("veedor_crear"), PERSONA)
        self.client.post(self.url("aspirante_crear"), PERSONA)
        response = self.client.get(self.concurso.get_absolute_url())
        for titulo in ("Integrantes del jurado", "Veedores de APUNSJ", "Aspirantes"):
            self.assertContains(response, f'<caption class="visually-hidden">{titulo}</caption>')
        self.assertContains(response, "<strong>Apellido Ficticio, Nombre Ficticio</strong>", count=3)

    def test_seis_plazas_independientes_y_sin_resultados_automaticos(self):
        for numero, representacion in enumerate(Jurado.Representacion.values):
            for calidad in Jurado.Calidad.values:
                datos = {**JURADO, "dni": str(30000000 + numero * 2 + (calidad == "suplente")),
                         "representacion": representacion, "calidad": calidad}
                self.assertEqual(self.client.post(self.url("jurado_crear"), datos).status_code, 302)
        self.assertEqual(Jurado.objects.count(), 6)
        self.assertEqual(self.concurso.historial.count(), 1)
        self.assertEqual(self.concurso.estado, "preparacion")

    def test_editar_participacion_no_modifica_persona_ni_otro_concurso(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            "representacion": jurado.representacion, "calidad": jurado.calidad,
            "titulo": "Título corregido", "unidad": "Unidad corregida", "email": "", "telefono": "",
            "version_esperada": jurado.version,
            "apellido": "No cambiar", "dni": "99999999",
        })
        self.assertEqual(response.status_code, 302)
        jurado.refresh_from_db()
        self.assertEqual(jurado.titulo, "Título corregido")
        self.assertEqual(jurado.persona.dni, "12345678")
        self.assertEqual(jurado.persona.apellido, PERSONA["apellido"])
        self.assertEqual(jurado.actualizado_por, self.operador)
        segundo = concurso_services.crear_concurso(datos={**DATOS, "expediente": "01-2-2026"}, usuario=self.operador)
        self.client.post(self.url("veedor_crear", segundo), {**PERSONA, "cargo": "Cargo original"})
        veedor = Veedor.objects.get()
        self.client.post(self.url("veedor_editar", segundo, veedor.pk), {
            "cargo": "Cargo nuevo", "email": "", "telefono": "", "version_esperada": veedor.version,
        })
        veedor.refresh_from_db()
        self.assertEqual(veedor.cargo, "Cargo nuevo")
        self.assertEqual(jurado.unidad, "Unidad corregida")

    def test_edicion_explicita_de_persona_y_dni_compartido_protegido(self):
        self.client.post(self.url("aspirante_crear"), PERSONA)
        persona = Persona.objects.get()
        self.assertEqual(self.client.post(self.url("persona_editar", None, persona.pk), {
            "apellido": "Apellido corregido", "nombre": PERSONA["nombre"], "dni": "87.654.321",
            "version_esperada": persona.version,
        }).status_code, 302)
        persona.refresh_from_db()
        self.assertEqual(persona.dni, "87654321")
        self.assertEqual(persona.actualizado_por, self.operador)
        segundo = concurso_services.crear_concurso(datos={**DATOS, "expediente": "01-2-2026"}, usuario=self.operador)
        self.client.post(self.url("aspirante_crear", segundo), {
            "apellido": persona.apellido, "nombre": persona.nombre, "dni": persona.dni,
        })
        response = self.client.post(self.url("persona_editar", None, persona.pk), {
            "apellido": "Otro apellido", "nombre": persona.nombre, "dni": "11111111",
            "version_esperada": persona.version,
        })
        self.assertIn("dni", response.context["form"].errors)
        persona.refresh_from_db()
        self.assertEqual(persona.dni, "87654321")
        response = self.client.post(self.url("persona_editar", None, persona.pk), {
            "apellido": "Otro apellido", "nombre": persona.nombre, "dni": persona.dni,
            "version_esperada": persona.version,
        })
        self.assertEqual(response.status_code, 302)
        persona.refresh_from_db()
        self.assertEqual(persona.apellido, "Otro apellido")

    def test_vistas_anidadas_permiso_lectura_escritura_e_idor(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        segundo = concurso_services.crear_concurso(datos={**DATOS, "expediente": "01-2-2026"}, usuario=self.operador)
        self.assertEqual(self.client.get(self.url("jurado_editar", segundo, jurado.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url("persona_editar", segundo, jurado.persona.pk)).status_code, 404)
        self.login(self.lector)
        self.assertEqual(self.client.get(self.concurso.get_absolute_url()).status_code, 200)
        self.assertNotContains(self.client.get(self.concurso.get_absolute_url()), "Agregar integrante")
        for name in ("jurado_crear", "veedor_crear", "aspirante_crear"):
            self.assertEqual(self.client.get(self.url(name)).status_code, 403)
            self.assertEqual(self.client.post(self.url(name), JURADO).status_code, 403)
        for name, pk in (("jurado_editar", jurado.pk), ("persona_editar", jurado.persona.pk)):
            self.assertEqual(self.client.get(self.url(name, None, pk)).status_code, 403)
        self.login(self.sin_permisos)
        self.assertEqual(self.client.get(self.concurso.get_absolute_url()).status_code, 403)
        self.assertEqual(self.client.post(self.url("aspirante_crear"), PERSONA).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url("aspirante_crear")).status_code, 302)

    def test_permisos_de_alta_y_edicion_son_independientes(self):
        permiso_alta = Permission.objects.get(content_type__app_label="concursos", codename="add_concurso")
        permiso_edicion = Permission.objects.get(content_type__app_label="concursos", codename="change_concurso")
        self.lector.user_permissions.add(permiso_alta)
        self.login(self.lector)
        self.assertEqual(self.client.post(self.url("aspirante_crear"), PERSONA).status_code, 302)
        persona = Persona.objects.get()
        self.assertEqual(self.client.get(self.url("persona_editar", None, persona.pk)).status_code, 403)
        self.lector.user_permissions.remove(permiso_alta)
        self.lector.user_permissions.add(permiso_edicion)
        self.login(self.lector)
        self.assertEqual(self.client.get(self.url("aspirante_crear")).status_code, 403)
        self.assertEqual(self.client.post(self.url("persona_editar", None, persona.pk), {
            "apellido": "Corregido", "nombre": persona.nombre, "dni": persona.dni,
            "version_esperada": persona.version,
        }).status_code, 302)

    def test_correccion_de_plaza_y_rechazo_de_plaza_ocupada(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            "representacion": "rectorado", "calidad": "suplente", "titulo": jurado.titulo,
            "unidad": jurado.unidad, "email": jurado.email, "telefono": jurado.telefono,
            "version_esperada": jurado.version,
        })
        self.assertEqual(response.status_code, 302)
        jurado.refresh_from_db()
        self.assertEqual((jurado.representacion, jurado.calidad), ("rectorado", "suplente"))
        self.assertEqual(jurado.version, 2)
        self.client.post(self.url("jurado_crear"), {
            **JURADO, "apellido": "Otra", "nombre": "Persona", "dni": "22.222.222",
            "representacion": "dependencia", "calidad": "titular",
        })
        otro = Jurado.objects.exclude(pk=jurado.pk).get()
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            "representacion": otro.representacion, "calidad": otro.calidad, "titulo": jurado.titulo,
            "unidad": jurado.unidad, "email": jurado.email, "telefono": jurado.telefono,
            "version_esperada": jurado.version,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        jurado.refresh_from_db()
        self.assertEqual((jurado.representacion, jurado.calidad), ("rectorado", "suplente"))

    def test_formularios_viejos_no_pisan_persona_jurado_o_veedor(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        self.client.post(self.url("veedor_crear"), {**PERSONA, "cargo": "Anterior"})
        jurado, veedor, persona = Jurado.objects.get(), Veedor.objects.get(), Persona.objects.get()
        cases = [
            ("jurado_editar", jurado, {"representacion": jurado.representacion, "calidad": jurado.calidad,
                                      "titulo": "Primera edición", "unidad": jurado.unidad, "email": "", "telefono": ""},
             {"representacion": jurado.representacion, "calidad": jurado.calidad,
              "titulo": "Edición vieja", "unidad": jurado.unidad, "email": "", "telefono": ""}),
            ("veedor_editar", veedor, {"cargo": "Primera edición", "email": "", "telefono": ""},
             {"cargo": "Edición vieja", "email": "", "telefono": ""}),
            ("persona_editar", persona, {"apellido": "Primera edición", "nombre": persona.nombre, "dni": persona.dni},
             {"apellido": "Edición vieja", "nombre": persona.nombre, "dni": persona.dni}),
        ]
        for nombre_url, registro, primero, viejo in cases:
            with self.subTest(registro=nombre_url):
                url = self.url(nombre_url, None, registro.pk)
                version_abierta = registro.version
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.post(url, {**primero, "version_esperada": version_abierta}).status_code, 302)
                response = self.client.post(url, {**viejo, "version_esperada": version_abierta})
                self.assertContains(response, "Otro operador modificó este registro")
                registro.refresh_from_db()
                self.assertEqual(registro.version, version_abierta + 1)
                campo = "titulo" if nombre_url == "jurado_editar" else "cargo" if nombre_url == "veedor_editar" else "apellido"
                self.assertEqual(getattr(registro, campo), "Primera edición")

    def test_version_faltante_no_omite_control_de_edicion(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        response = self.client.post(self.url("jurado_editar", None, jurado.pk), {
            "representacion": jurado.representacion, "calidad": jurado.calidad,
            "titulo": "Sin versión", "unidad": jurado.unidad, "email": "", "telefono": "",
        })
        self.assertIn("version_esperada", response.context["form"].errors)
        jurado.refresh_from_db()
        self.assertEqual(jurado.version, 1)

    def test_navegacion_de_participantes_renueva_pero_consulta_automatica_no(self):
        session_key = self.client.session.session_key
        self.now.return_value = START + timedelta(seconds=1799)
        url = self.url("jurado_crear")
        self.client.get(url)
        self.assertEqual(SessionActivity.objects.get(session_id=session_key).last_activity, START)
        self.client.get(url, HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1", HTTP_SEC_PURPOSE="prefetch")
        self.assertEqual(SessionActivity.objects.get(session_id=session_key).last_activity, START)
        self.client.get(url, HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1")
        self.assertEqual(SessionActivity.objects.get(session_id=session_key).last_activity, START + timedelta(seconds=1799))

    def test_csrf_y_sesion_expirada_bloquean_escrituras(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        client.post(reverse("login"), {
            "username": self.operador.username, "password": PASSWORD, "csrfmiddlewaretoken": token,
        })
        self.assertEqual(client.post(self.url("aspirante_crear"), PERSONA).status_code, 403)
        self.assertEqual(Aspirante.objects.count(), 0)
        for name in ("jurado_crear", "veedor_crear", "aspirante_crear"):
            self.now.return_value = START
            self.login(self.operador)
            self.now.return_value = START + timedelta(seconds=1800)
            response = self.client.post(self.url(name), JURADO)
            self.assertEqual(response.url, "/ingresar/?expired=1")
        self.assertEqual(Persona.objects.count(), 0)

    def test_no_hay_borrado_de_personas_o_participaciones(self):
        self.client.post(self.url("aspirante_crear"), PERSONA)
        persona = Persona.objects.get()
        self.assertEqual(self.client.get(self.url("aspirante_crear").replace("nuevo/", "1/eliminar/")).status_code, 404)
        self.assertEqual(Persona._meta.default_permissions, ())
        self.assertEqual(Aspirante._meta.default_permissions, ())
        with self.assertRaises(ProtectedError):
            persona.delete()
        with self.assertRaises(ProtectedError):
            self.concurso.delete()

    def test_mascara_y_validacion_de_telefonos_en_altas(self):
        self.assertContains(self.client.get(self.url("jurado_crear")), 'maxlength="11"')
        invalido = self.client.post(self.url("jurado_crear"), {**JURADO, "telefono": "264-1234"})
        self.assertIn("telefono", invalido.context["form"].errors)
        self.assertEqual(Jurado.objects.count(), 0)
        correcto = self.client.post(self.url("jurado_crear"), {**JURADO, "telefono": "2641234567"})
        self.assertEqual(correcto.status_code, 302)
        self.assertEqual(Jurado.objects.get().telefono, "264-1234567")

    def test_telefono_historico_de_jurado_se_preserva_al_editar(self):
        self.client.post(self.url("jurado_crear"), JURADO)
        jurado = Jurado.objects.get()
        Jurado.objects.filter(pk=jurado.pk).update(telefono="2")
        jurado.refresh_from_db()
        url = self.url("jurado_editar", None, jurado.pk)
        self.assertContains(self.client.get(url), 'data-legacy-value="2"')
        response = self.client.post(url, {
            "representacion": jurado.representacion, "calidad": jurado.calidad,
            "titulo": "Título modificado", "unidad": jurado.unidad,
            "email": jurado.email, "telefono": "2", "version_esperada": jurado.version,
        })
        self.assertEqual(response.status_code, 302)
        jurado.refresh_from_db()
        self.assertEqual(jurado.telefono, "2")
        self.assertEqual(jurado.titulo, "Título modificado")
        response = self.client.post(url, {
            "representacion": jurado.representacion, "calidad": jurado.calidad,
            "titulo": "Otro", "unidad": jurado.unidad, "email": "",
            "telefono": "3", "version_esperada": jurado.version,
        })
        self.assertIn("telefono", response.context["form"].errors)
        jurado.refresh_from_db()
        self.assertEqual(jurado.telefono, "2")
