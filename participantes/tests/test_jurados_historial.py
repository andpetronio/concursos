from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from participantes.jurados_services import registrar_presentacion, resolver_presentacion, designar_reemplazante
from participantes.models import ActuacionJurado, Jurado, Persona
from participantes.services import editar_participacion, crear_participacion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HistorialJuradosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="usuario_jurados", password="ClavePruebaJurados-2026!"
        )
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        cls.lector = get_user_model().objects.create_user(username="lector_jurados", password="ClavePruebaJurados-2026!")
        cls.lector.user_permissions.add(Permission.objects.get(content_type__app_label="concursos", codename="view_concurso"))
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.usuario)
        for indice, calidad in enumerate(("titular", "suplente")):
            persona = Persona.objects.create(
                apellido="Original", nombre=f"Jurado {calidad}", dni=f"3355000{indice}",
                creado_por=cls.usuario, actualizado_por=cls.usuario,
            )
            Jurado.todos.create(concurso=cls.concurso, persona=persona, representacion="rectorado",
                               calidad=calidad, titulo="Licenciado", unidad="Rectorado",
                               creado_por=cls.usuario, actualizado_por=cls.usuario)

    def titular(self):
        return Jurado.objects.get(concurso=self.concurso, representacion="rectorado", calidad="titular")

    def suplente(self):
        return Jurado.objects.get(concurso=self.concurso, representacion="rectorado", calidad="suplente")

    def presentar(self, jurado, *, motivo="excusacion"):
        return registrar_presentacion(jurado_id=jurado.pk, concurso_id=self.concurso.pk,
                                     usuario=self.usuario, version_esperada=jurado.version,
                                     motivo=motivo, fecha_actuacion=date(2026, 10, 30), fojas="11")

    def resolver(self, jurado, presentacion, *, promover=False):
        return resolver_presentacion(jurado_id=jurado.pk, concurso_id=self.concurso.pk,
                                    presentacion_id=presentacion.pk, usuario=self.usuario,
                                    version_esperada=jurado.version, resolucion="3550/26-R",
                                    fecha_resolucion=date(2026, 10, 30), fojas="19/21",
                                    promover_suplente=promover)

    def test_presentacion_pendiente_no_modifica_plazas(self):
        titular = self.titular()
        solicitud = self.presentar(titular)
        self.assertIsNone(solicitud.resuelto_por_id)
        self.assertEqual(Jurado.objects.filter(concurso=self.concurso).count(), 2)
        self.assertEqual(self.titular().pk, titular.pk)
        with self.assertRaises(ValidationError):
            self.presentar(titular)

    def test_resolucion_cesa_primero_y_asciende_suplente_sin_perder_historia(self):
        titular, suplente = self.titular(), self.suplente()
        solicitud = self.presentar(titular, motivo="recusacion")
        with self.assertRaises(ValidationError):
            self.resolver(titular, solicitud, promover=False)
        self.assertTrue(Jurado.todos.get(pk=titular.pk).vigente)
        self.resolver(titular, solicitud, promover=True)
        self.assertEqual(self.titular().pk, suplente.pk)
        self.assertFalse(Jurado.todos.get(pk=titular.pk).vigente)
        self.assertEqual(Jurado.todos.filter(concurso=self.concurso).count(), 2)
        self.assertEqual(Jurado.objects.filter(concurso=self.concurso).count(), 1)
        self.assertEqual(self.concurso.jurados.count(), 1)
        self.assertFalse(Jurado.objects.filter(concurso=self.concurso, calidad="suplente").exists())
        self.assertEqual(ActuacionJurado.objects.filter(concurso=self.concurso).count(), 3)
        solicitud.refresh_from_db()
        self.assertIsNotNone(solicitud.resuelto_por_id)
        self.assertEqual(ActuacionJurado.objects.get(tipo="promocion").calidad_anterior, "suplente")
        with self.assertRaises(ValidationError):
            self.resolver(titular, solicitud, promover=True)

    def test_cese_del_suplente_no_modifica_al_titular_y_posterior_baja_de_ambos(self):
        suplente = self.suplente()
        self.resolver(suplente, self.presentar(suplente, motivo="recusacion"))
        self.assertTrue(Jurado.todos.get(pk=self.titular().pk).vigente)
        self.assertFalse(Jurado.objects.filter(calidad="suplente").exists())
        titular = self.titular()
        self.resolver(titular, self.presentar(titular))
        self.assertFalse(Jurado.objects.filter(concurso=self.concurso).exists())
        self.assertEqual(Jurado.todos.filter(concurso=self.concurso).count(), 2)

    def test_si_ambos_presentan_excusacion_no_promueve_suplente_pendiente(self):
        titular, suplente = self.titular(), self.suplente()
        presentacion_titular = self.presentar(titular)
        presentacion_suplente = self.presentar(suplente)
        with self.assertRaisesMessage(ValidationError, "El suplente también tiene una presentación"):
            self.resolver(titular, presentacion_titular, promover=True)
        self.assertEqual(Jurado.objects.filter(concurso=self.concurso).count(), 2)
        self.resolver(suplente, presentacion_suplente)
        self.resolver(titular, presentacion_titular)
        self.assertFalse(Jurado.objects.filter(concurso=self.concurso).exists())

    def test_reemplazante_requiere_plaza_vacante_resolucion_y_conserva_anterior(self):
        titular, suplente = self.titular(), self.suplente()
        with self.assertRaises(ValidationError):
            designar_reemplazante(concurso=self.concurso, representacion="rectorado", calidad="suplente",
                                 datos={"apellido":"Nuevo", "nombre":"Jurado", "dni":"44332211",
                                        "titulo":"Doctor", "unidad":"Rectorado"}, usuario=self.usuario,
                                 resolucion="12/26-R", fecha_resolucion=date(2026, 10, 30))
        self.resolver(titular, self.presentar(titular), promover=True)
        datos = {"apellido":"Nuevo", "nombre":"Jurado", "dni":"44332211",
                 "titulo":"Doctor", "unidad":"Rectorado", "email":"", "telefono":""}
        with self.assertRaises(ValidationError):
            crear_participacion(modelo=Jurado, concurso=self.concurso, datos={**datos,
                "representacion":"rectorado", "calidad":"suplente"}, usuario=self.usuario)
        nuevo = designar_reemplazante(concurso=self.concurso, representacion="rectorado",
                                     calidad="suplente", datos=datos, usuario=self.usuario,
                                     resolucion="4050/26-R", fecha_resolucion=date(2026, 10, 30))
        self.assertEqual(self.suplente().pk, nuevo.pk)
        self.assertEqual(Jurado.todos.filter(concurso=self.concurso).count(), 3)
        self.assertEqual(ActuacionJurado.objects.filter(tipo="designacion").count(), 1)
        self.client.post(reverse("login"), {"username": self.usuario.username,
                "password": "ClavePruebaJurados-2026!"})
        self.assertContains(self.client.get(self.concurso.get_absolute_url()),
                            "Historial de integración del jurado")

    def test_edicion_comun_no_cambia_caracter_ni_representacion(self):
        suplente = self.suplente()
        with self.assertRaises(ValidationError):
            editar_participacion(participacion=suplente, datos={"calidad":"titular"},
                                 usuario=self.usuario, version_esperada=suplente.version)
        suplente.refresh_from_db()
        self.assertEqual(suplente.calidad, "suplente")
        with self.assertRaises(ValidationError):
            editar_participacion(participacion=suplente, datos={"representacion":"personal"},
                                 usuario=self.usuario, version_esperada=suplente.version)

    def test_permisos_y_vistas_compactas(self):
        titular = self.titular()
        ruta = reverse("concursos:jurado_presentacion", args=[self.concurso.pk, titular.pk])
        self.client.post(reverse("login"), {"username": self.lector.username, "password":"ClavePruebaJurados-2026!"})
        self.assertEqual(self.client.get(ruta).status_code, 403)
        # El LoginView redirige a quien ya está autenticado: cerrar la sesión de lectura.
        self.client.logout()
        self.client.post(reverse("login"), {"username": self.usuario.username, "password":"ClavePruebaJurados-2026!"})
        self.assertContains(self.client.get(self.concurso.get_absolute_url()), "Registrar presentación del jurado")
        self.assertContains(self.client.get(ruta), "Registrar excusación o recusación")
        respuesta = self.client.post(ruta, {"version_esperada": titular.version, "motivo":"excusacion",
                                         "fecha_actuacion":"2026-10-30", "fojas":"18", "observaciones":""})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.titular().vigente)
        resolver = reverse("concursos:jurado_resolver", args=[self.concurso.pk, titular.pk])
        self.assertContains(self.client.get(resolver), "Registrar resolución rectoral")
        respuesta = self.client.post(resolver, {"version_esperada": titular.version,
            "presentacion_id": ActuacionJurado.objects.get(tipo="presentacion").pk,
            "resolucion":"3000/26-R", "fecha_resolucion":"2026-10-30",
            "fojas":"19", "observaciones":"", "promover_suplente":"on"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.titular().persona.nombre, "Jurado suplente")
        self.assertEqual(self.client.get(ruta).status_code, 404)  # Ya no vigente.

    def test_lector_no_puede_escribir_via_servicio(self):
        with self.assertRaises(PermissionDenied):
            registrar_presentacion(jurado_id=self.titular().pk, concurso_id=self.concurso.pk,
                                   usuario=self.lector, version_esperada=1,
                                   motivo="excusacion", fecha_actuacion=date(2026, 10, 30))
