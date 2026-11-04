"""F4M.2: revisión visual segura de antecedentes del jurado."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from participantes.jurados_services import registrar_presentacion, resolver_presentacion
from participantes.models import ActuacionJurado, Jurado, Persona


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConsiderandosJuradoPreviewTests(TestCase):
    CLAVE = "ClavePruebaF4M2-2026!"

    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user(
            username="operador_f4m2", password=cls.CLAVE,
        )
        cls.operador.user_permissions.set(
            Permission.objects.filter(content_type__app_label="concursos")
        )
        cls.lector = get_user_model().objects.create_user(
            username="lector_f4m2", password=cls.CLAVE,
        )
        cls.lector.user_permissions.add(
            Permission.objects.get(content_type__app_label="concursos", codename="view_concurso")
        )
        cls.sin_permiso = get_user_model().objects.create_user(
            username="sin_permiso_f4m2", password=cls.CLAVE,
        )
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.operador)
        cls.integrantes = []
        for indice, (nombre, apellido, calidad) in enumerate((
            ("Juan", "Pérez", "titular"), ("María", "Gómez", "suplente"),
        )):
            persona = Persona.objects.create(
                nombre=nombre, apellido=apellido, dni=f"3344900{indice}",
                creado_por=cls.operador, actualizado_por=cls.operador,
            )
            cls.integrantes.append(Jurado.todos.create(
                concurso=cls.concurso, persona=persona, representacion="rectorado",
                calidad=calidad, titulo="Licenciado", unidad="Rectorado",
                creado_por=cls.operador, actualizado_por=cls.operador,
            ))

    @property
    def ruta(self):
        return reverse("concursos:jurados_considerandos", args=[self.concurso.pk])

    def ingresar(self, usuario=None):
        self.client.logout()
        usuario = usuario or self.operador
        respuesta = self.client.post(reverse("login"), {
            "username": usuario.username, "password": self.CLAVE,
        })
        self.assertEqual(respuesta.status_code, 302)

    def excusar_y_resolver(self):
        titular = self.integrantes[0]
        presentacion = registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk, usuario=self.operador,
            version_esperada=titular.version, motivo="excusacion",
            fecha_actuacion=date(2026, 10, 20), fojas="45",
        )
        resolver_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            presentacion_id=presentacion.pk, usuario=self.operador,
            version_esperada=titular.version, resolucion="3278/26-R",
            fecha_resolucion=date(2026, 10, 30), fojas="48/49",
            promover_suplente=True,
        )

    def test_enlace_desde_ficha_y_pantalla_sin_actuaciones(self):
        self.ingresar(self.lector)
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(ficha, self.ruta)
        respuesta = self.client.get(self.ruta)
        self.assertContains(respuesta, "Antecedentes del jurado para documentos")
        self.assertContains(respuesta, "no registra modificaciones del jurado")
        self.assertNotContains(respuesta, "Que mediante Resolución N.º")

    def test_excusacion_y_promocion_generan_un_bloque_revisable(self):
        self.excusar_y_resolver()
        self.ingresar()
        respuesta = self.client.get(self.ruta)
        self.assertEqual(respuesta.status_code, 200)
        previa = respuesta.context["vista_previa"]
        self.assertEqual(len(previa.bloques), 1)
        self.assertEqual(len(previa.bloques[0].considerandos), 3)
        self.assertContains(respuesta, "Juan Pérez")
        self.assertContains(respuesta, "María Gómez")
        self.assertContains(respuesta, "3278/26-R")
        self.assertContains(respuesta, "48/49")
        self.assertContains(respuesta, "45")
        self.assertContains(respuesta, "por el mismo acto resolutivo", count=1)

    def test_fecha_documento_excluye_resoluciones_posteriores(self):
        self.excusar_y_resolver()
        self.ingresar()
        respuesta = self.client.get(self.ruta, {"fecha_documento": "2026-10-21"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["vista_previa"].bloques), 0)
        self.assertNotContains(respuesta, "Que mediante Resolución N.º 3278/26-R")
        self.assertContains(respuesta, "No hay resoluciones que permitan proponer considerandos")

    def test_fecha_invalida_no_muestra_resultados_sin_filtro(self):
        self.excusar_y_resolver()
        self.ingresar()
        respuesta = self.client.get(self.ruta, {"fecha_documento": "fecha-invalida"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context["vista_previa"])
        self.assertContains(respuesta, "Corregí la fecha ingresada")
        self.assertNotContains(respuesta, "Que mediante Resolución N.º 3278/26-R")

    def test_presentacion_pendiente_solo_genera_advertencia(self):
        titular = self.integrantes[0]
        registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk, usuario=self.operador,
            version_esperada=titular.version, motivo="excusacion",
            fecha_actuacion=date(2026, 10, 20), fojas="10",
        )
        self.ingresar()
        respuesta = self.client.get(self.ruta)
        self.assertContains(respuesta, "Presentación pendiente de resolución")
        self.assertNotContains(respuesta, "Que mediante Resolución N.º")

    def test_fojas_faltantes_bloquean_el_borrador_de_ese_acto(self):
        ActuacionJurado.objects.create(
            concurso=self.concurso, jurado=self.integrantes[0], tipo="designacion",
            representacion="rectorado", calidad_nueva="titular",
            fecha_actuacion=date(2026, 10, 30), resolucion="3278/26-R",
            fojas="", registrado_por=self.operador,
        )
        self.ingresar()
        respuesta = self.client.get(self.ruta)
        self.assertContains(respuesta, "Fojas de la resolución rectoral")
        self.assertContains(respuesta, "No se propone una redacción incompleta")
        self.assertNotContains(respuesta, "Que mediante Resolución N.º 3278/26-R")

    def test_no_permiso_es_403_y_lector_puede_ver(self):
        self.ingresar(self.sin_permiso)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)
        self.ingresar(self.lector)
        self.assertEqual(self.client.get(self.ruta).status_code, 200)

    def test_consulta_no_escribe_actuaciones(self):
        self.excusar_y_resolver()
        total = ActuacionJurado.objects.filter(concurso=self.concurso).count()
        self.ingresar()
        self.client.get(self.ruta)
        self.assertEqual(ActuacionJurado.objects.filter(concurso=self.concurso).count(), total)
