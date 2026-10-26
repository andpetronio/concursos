from datetime import timedelta
import hashlib
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from docx import Document
from docx.shared import Cm, Pt

from concursos import services as concurso_services
from concursos.models import Concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from core.models import SessionActivity
from expedientes import services as expediente_services
from . import services
from .models import DestinatarioAPUNSJ, DestinatarioPersonal, GeneracionDocumento, MembreteInstitucional
from .registry import POR_CODIGO
from .registry import TIPOS

DESTINATARIO = {"tratamiento": "Sr.", "cargo": "Secretario General", "titulo": "Lic.",
                "nombre": "Nombre ficticio", "apellido": "Apellido ficticio"}


def editable_font_family(registro):
    documento = Document(BytesIO(bytes(registro.contenido)))
    return documento.styles["Normal"].font.name


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DocumentosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user("documental_ficticio", password=PASSWORD)
        cls.operador.user_permissions.set(Permission.objects.filter(
            content_type__app_label__in=["concursos", "documentos"]))
        cls.lector = get_user_model().objects.create_user("lector_documental", password=PASSWORD)
        cls.lector.user_permissions.add(Permission.objects.get(codename="view_concurso"))
        cls.configurador = get_user_model().objects.create_user("configurador", password=PASSWORD)
        cls.configurador.user_permissions.add(Permission.objects.get(codename="configurar_institucion"))

    def setUp(self):
        self.concurso = concurso_services.crear_concurso(datos=DATOS, usuario=self.operador)
        self.destinatario = services.guardar_destinatario(datos=DESTINATARIO, usuario=self.operador, version_esperada=0)
        self.concurso.resolucion_convocatoria = "3279/26-R"
        self.concurso.save(update_fields=["resolucion_convocatoria"])
        imagen = (Path(__file__).parent / "assets" / "unsj-crest-wordmark.png").read_bytes()
        self.membrete = services.guardar_membrete(
            imagen={"contenido": imagen, "tipo_mime": "image/png", "nombre_archivo": "membrete-ficticio.png"},
            usuario=self.operador, version_esperada=0)
        self.login(self.operador)

    def login(self, usuario, client=None):
        client = client or self.client
        client.logout()
        client.post(reverse("login"), {"username": usuario.username, "password": PASSWORD})

    def huella(self, tipo="apunsj"):
        from .registry import POR_CODIGO
        actual = Concurso.objects.get(pk=self.concurso.pk)
        snapshot, _, _, _ = services.fuentes_actuales(actual, POR_CODIGO[tipo])
        return services.huella_fuentes(snapshot)

    def generar(self, **kwargs):
        kwargs.setdefault("huella_esperada", self.huella())
        return services.generar(concurso_id=self.concurso.pk, tipo_codigo="apunsj", usuario=self.operador,
                                version_concurso=self.concurso.version,
                                version_destinatario=self.destinatario.version, **kwargs)

    def url_revision(self, tipo="apunsj"):
        return reverse("documentos:revisar", args=[self.concurso.pk, tipo])

    def post_generacion(self, **kwargs):
        return self.client.post(self.url_revision(), {
            "huella_esperada": self.huella(), "version_concurso": self.concurso.version,
            "version_destinatario": self.destinatario.version, **kwargs})

    def texto(self, registro):
        documento = Document(BytesIO(bytes(registro.contenido)))
        return "\n".join([p.text for p in documento.paragraphs] + [
            c.text for tabla in documento.tables for fila in tabla.rows for c in fila.cells])

    def test_oficio_apunsj_exige_resolucion_y_membrete(self):
        self.concurso.resolucion_convocatoria = ""
        self.concurso.save(update_fields=["resolucion_convocatoria"])
        estado = services.disponibilidad(self.concurso, POR_CODIGO["apunsj"], self.destinatario)
        self.assertFalse(estado["disponible"])
        self.assertTrue(any("resolución oficial" in x for x in estado["faltantes"]))
        with self.assertRaisesMessage(ValidationError, "resolución oficial"):
            self.generar()
        self.concurso.resolucion_convocatoria = "3279/26-R"
        self.concurso.save(update_fields=["resolucion_convocatoria"])
        MembreteInstitucional.objects.all().delete()
        with self.assertRaisesMessage(ValidationError, "Cargar el membrete"):
            self.generar()
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_oficio_apunsj_ignora_resolucion_y_fecha_inventadas_por_cliente(self):
        registro = self.generar(complementarios={"res_convocatoria": "9999/26-R", "lugar_fecha": "Otra fecha"})
        texto = self.texto(registro)
        self.assertIn("3279/26-R", texto)
        self.assertNotIn("9999/26-R", texto)
        self.assertNotIn("Otra fecha", texto)
        self.assertEqual(registro.instantanea["complementarios"]["res_convocatoria"], "3279/26-R")
        self.assertEqual(registro.instantanea["pendientes"], [])

    def test_docx_editable_y_encabezados_para_ambos_tratamientos(self):
        for tratamiento, cargo in [("Sr.", "Secretario General"), ("Sra.", "Secretaria General")]:
            with self.subTest(tratamiento=tratamiento):
                self.destinatario = services.guardar_destinatario(
                    datos={**DESTINATARIO, "tratamiento": tratamiento, "cargo": cargo, "titulo": ""},
                    usuario=self.operador, version_esperada=self.destinatario.version)
                registro = self.generar()
                texto = self.texto(registro)
                self.assertIn(f"{cargo} de la", texto)
                self.assertIn("Asociación del Personal Nodocente de la UNSJ", texto)
                self.assertIn("Nombre ficticio Apellido ficticio", texto)
                self.assertIn("Presente", texto)
                self.assertNotIn("BORRADOR NO EMITIDO", texto)
                self.assertIn(self.concurso.expediente, texto)
                self.assertIn("Ordenanza Nº 33/10-CS", texto)
                self.assertIn("el artículo 25º de la Ordenanza Nº 33/10-CS", texto)
                self.assertIn("artículo 31º", texto)
                self.assertIn("correo electrónico", texto)
                self.assertIn("Resolución Nº 3279/26-R", texto)
                self.assertNotIn("no existe un modelo específico aprobado", texto)
                self.assertEqual(registro.instantanea["membrete"]["sha256"], self.membrete.sha256)
                self.assertIn("San Juan,", registro.instantanea["complementarios"]["lugar_fecha"])
                self.assertEqual(registro.plantilla_version, "apunsj-3")
                self.assertEqual(editable_font_family(registro), "Arial")
                self.assertNotIn("{{", texto)
                with ZipFile(BytesIO(bytes(registro.contenido))) as archivo:
                    self.assertIn("word/document.xml", archivo.namelist())
                editable = Document(BytesIO(bytes(registro.contenido)))
                editable.add_paragraph("Edición de prueba")
                salida = BytesIO()
                editable.save(salida)
                self.assertIn("Edición de prueba", Document(BytesIO(salida.getvalue())).paragraphs[-1].text)

    def test_nueva_redaccion_apunsj_respeta_parrafos_y_variables(self):
        registro = self.generar()
        documento = Document(BytesIO(bytes(registro.contenido)))
        contenido = "\n".join(p.text for p in documento.paragraphs)
        self.assertIn("Me dirijo a usted con el propósito de solicitarle tenga a bien comunicar", contenido)
        self.assertIn("designación de un veedor en representación de la Asociación que preside", contenido)
        self.assertIn("Convenio Colectivo de Trabajo para el Personal Nodocente", contenido)
        self.assertIn("homologado por Decreto Nº 366/06-PEN", contenido)
        self.assertIn(f"Concurso {self.concurso.get_modalidad_display()} de antecedentes y oposición", contenido)
        self.assertIn(f"Expediente Nº {self.concurso.expediente}", contenido)
        self.assertIn(f"Código Presupuestario Nº {self.concurso.codigo_presupuestario}", contenido)
        self.assertIn(f"con funciones de “{self.concurso.denominacion}”", contenido)
        self.assertIn("así como una dirección de correo electrónico institucional", contenido)
        self.assertIn("Resolución Nº 3279/26-R", contenido)
        self.assertIn("la mayor brevedad posible", contenido)
        self.assertIn("Sin otro particular, saludo a usted atentamente.", contenido)
        self.assertNotIn("Atento a que por Expediente", contenido)
        self.assertNotIn("A los efectos de la prosecución", contenido)
        self.assertNotIn("17-697-2024", contenido)
        self.assertNotIn("2339/26-R", contenido)
        self.assertEqual(registro.plantilla_version, "apunsj-3")

    def test_destinatario_incompleto_y_cargo_incompatible(self):
        for campo in ["nombre", "apellido", "tratamiento", "cargo"]:
            with self.subTest(campo=campo), self.assertRaises(ValidationError):
                services.guardar_destinatario(datos={**DESTINATARIO, campo: ""},
                    usuario=self.operador, version_esperada=self.destinatario.version)
        with self.assertRaises(ValidationError):
            services.guardar_destinatario(datos={**DESTINATARIO, "cargo": "Secretaria General"},
                usuario=self.operador, version_esperada=self.destinatario.version)
        DestinatarioAPUNSJ.objects.all().delete()
        with self.assertRaises(ValidationError):
            self.generar()
        self.assertEqual(GeneracionDocumento.objects.count(), 0)

    def test_configuracion_permiso_especifico_y_no_asignacion_automatica(self):
        url = reverse("documentos:configuracion")
        edicion = reverse("documentos:configuracion_apunsj")
        self.login(self.lector)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(edicion).status_code, 403)
        with self.assertRaises(PermissionDenied):
            services.guardar_destinatario(datos=DESTINATARIO, usuario=self.lector, version_esperada=1)
        self.login(self.configurador)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(edicion).status_code, 200)
        self.assertEqual(self.client.post(url, {**DESTINATARIO, "nombre": "Otra autoridad", "version_esperada": 1}).status_code, 405)
        self.assertRedirects(self.client.post(edicion, {**DESTINATARIO, "nombre": "Otra autoridad", "version_esperada": 1}), edicion)
        self.assertEqual(DestinatarioAPUNSJ.objects.get(pk=1).nombre, "Otra autoridad")
        self.assertEqual(self.client.get(self.url_revision()).status_code, 403)
        self.assertFalse(self.lector.has_perm("documentos.generar_documento"))

    def test_configuracion_institucional_muestra_tres_parametros_del_mismo_nivel(self):
        respuesta = self.client.get(reverse("documentos:configuracion"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "documentos/configuracion.html")
        self.assertNotIn("form", respuesta.context)
        self.assertContains(respuesta, 'class="card institution-settings-card"', count=3)
        for titulo, destino in (
            ("Secretaría General de APUNSJ", "documentos:configuracion_apunsj"),
            ("Jefatura del Departamento de Personal", "documentos:configuracion_personal"),
            ("Membrete institucional", "documentos:membrete"),
        ):
            self.assertContains(respuesta, titulo)
            self.assertContains(respuesta, f'href="{reverse(destino)}"')
        self.assertContains(respuesta, "Pendiente de configuración")  # Personal sin cargar.
        self.assertContains(respuesta, self.destinatario.nombre)
        self.assertContains(respuesta, self.membrete.nombre_archivo)
        self.assertNotContains(respuesta, "Guardar configuración")

    def test_configuracion_apunsj_preserva_versionado_y_navegacion(self):
        edicion = reverse("documentos:configuracion_apunsj")
        respuesta = self.client.get(edicion)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "documentos/configuracion_apunsj.html")
        self.assertContains(respuesta, "Volver a configuración institucional")
        self.assertContains(respuesta, 'class="nav-link is-active" href="/concursos/configuracion-institucional/" aria-current="page"')
        self.assertEqual(respuesta.context["form"]["version_esperada"].value(), 1)
        respuesta = self.client.post(edicion, {**DESTINATARIO, "nombre": "Nombre corregido", "version_esperada": 0})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].non_field_errors())
        self.assertEqual(DestinatarioAPUNSJ.objects.get(pk=1).nombre, self.destinatario.nombre)

    def test_configuracion_version_obsoleta_no_sobrescribe(self):
        services.guardar_destinatario(datos={**DESTINATARIO, "nombre": "Autoridad nueva"}, usuario=self.operador, version_esperada=1)
        with self.assertRaises(ValidationError):
            services.guardar_destinatario(datos=DESTINATARIO, usuario=self.operador, version_esperada=1)
        self.assertEqual(DestinatarioAPUNSJ.objects.get().nombre, "Autoridad nueva")

    def test_generacion_rechaza_cambios_desde_revision(self):
        services.guardar_destinatario(datos={**DESTINATARIO, "nombre": "Nueva"}, usuario=self.operador, version_esperada=1)
        with self.assertRaises(ValidationError):
            self.generar()
        self.destinatario.refresh_from_db()
        Concurso.objects.filter(pk=self.concurso.pk).update(version=2)
        with self.assertRaises(ValidationError):
            self.generar()
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_historia_bytes_hash_inalterados_tras_cambios(self):
        registro = self.generar()
        contenido, snapshot = bytes(registro.contenido), registro.instantanea
        services.guardar_destinatario(datos={**DESTINATARIO, "nombre": "Nueva autoridad"}, usuario=self.operador, version_esperada=1)
        concurso_services.editar_concurso(pk=self.concurso.pk, datos={**DATOS, "denominacion": "Otro cargo"},
                                         usuario=self.operador, version_esperada=self.concurso.version)
        registro.refresh_from_db()
        self.assertEqual(bytes(registro.contenido), contenido)
        self.assertEqual(registro.instantanea, snapshot)
        self.assertEqual(registro.sha256, hashlib.sha256(contenido).hexdigest())
        self.assertEqual(registro.plantilla_version, "apunsj-3")
        for operacion in [registro.save, registro.delete,
                          lambda: GeneracionDocumento.objects.filter(pk=registro.pk).update(tipo="otro"),
                          lambda: GeneracionDocumento.objects.filter(pk=registro.pk).delete()]:
            with self.assertRaises(ValidationError):
                operacion()

    def test_no_modifica_checklist_estados_participantes_ni_historial(self):
        controles = list(self.concurso.controles_documentales.values())
        historial = list(self.concurso.historial.values())
        antes = Concurso.objects.values().get(pk=self.concurso.pk)
        registro = self.generar()
        self.assertEqual(list(self.concurso.controles_documentales.values()), controles)
        self.assertEqual(list(self.concurso.historial.values()), historial)
        self.assertEqual(Concurso.objects.values().get(pk=self.concurso.pk), antes)
        self.assertEqual(self.concurso.jurados.count() + self.concurso.aspirantes.count() + self.concurso.veedors.count(), 0)
        self.assertEqual(registro.instantanea["actuaciones_verificadas"], [])

    def test_fojas_solo_de_actuaciones_verificadas_preservadas(self):
        control = self.concurso.controles_documentales.filter(requisito="jurado_dependencia").first()
        if control is None:
            control = self.concurso.controles_documentales.first()
        control.verificado, control.fojas = True, "5/8"
        control.save()
        registro = self.generar()
        self.assertEqual(registro.instantanea["actuaciones_verificadas"][0]["fojas"], "5/8")

    @patch("pathlib.Path.is_file", return_value=False)
    def test_fuentes_ausentes_bloquean_cinco_tipos_y_convocatoria_consulta_servicio(self, fuente_ausente):
        self.assertEqual(len(TIPOS), 6)
        for tipo in TIPOS:
            with self.subTest(tipo=tipo.codigo):
                with patch.object(expediente_services, "habilitacion_convocatoria", wraps=expediente_services.habilitacion_convocatoria) as habilitar:
                    estado = services.disponibilidad(self.concurso, tipo, self.destinatario)
                    self.assertFalse(estado["disponible"])
                    self.assertIn(tipo.fuente, estado["faltantes"][0])
                    if tipo.codigo == "convocatoria":
                        habilitar.assert_called_once_with(self.concurso)
                        self.assertGreaterEqual(len(estado["faltantes"]), 12)
                with self.assertRaises(ValidationError):
                    services.generar(concurso_id=self.concurso.pk, tipo_codigo=tipo.codigo,
                                     usuario=self.operador, version_concurso=1, version_destinatario=1)
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_apunsj_modelo_incluye_modalidad_acotado_sin_revision_excepcional(self):
        self.concurso.modalidad = "acotado"
        self.concurso.save()
        registro = self.generar()
        self.assertIn("Concurso Acotado", self.texto(registro))
        self.assertNotIn("no existe un modelo específico aprobado", self.texto(registro))
        self.assertFalse(registro.instantanea["complementarios"]["revision_administrativa"])

    def test_permisos_lectura_generacion_y_descarga_aislamiento(self):
        registro = self.generar()
        url = reverse("documentos:descargar", args=[self.concurso.pk, registro.pk])
        self.login(self.lector)
        self.assertEqual(self.client.get(self.concurso.get_absolute_url()).status_code, 200)
        for metodo, ruta in [("get", self.url_revision()), ("post", self.url_revision()), ("get", url)]:
            self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 403)
        self.login(self.operador)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.content, bytes(registro.contenido))
        self.assertIn(f'concurso-{self.concurso.pk}-documento-{registro.pk}.docx', respuesta["Content-Disposition"])
        self.assertIn("no-store", respuesta["Cache-Control"])
        otro = concurso_services.crear_concurso(datos=DATOS, usuario=self.operador)
        self.assertEqual(self.client.get(reverse("documentos:descargar", args=[otro.pk, registro.pk])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_get_no_genera_post_csrf_y_descarga_no_regenera(self):
        self.assertEqual(self.client.get(self.url_revision()).status_code, 200)
        self.assertEqual(GeneracionDocumento.objects.count(), 0)
        client = Client(enforce_csrf_checks=True)
        self.login(self.operador, client)
        # Login without CSRF was rejected; authenticate with the real login token.
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD,
                                       "csrfmiddlewaretoken": token})
        self.assertEqual(client.post(self.url_revision(), {"version_concurso": 1, "version_destinatario": 1}).status_code, 403)
        self.assertEqual(client.post(reverse("documentos:configuracion_apunsj"), DESTINATARIO).status_code, 403)
        respuesta = self.post_generacion()
        self.assertEqual(respuesta.status_code, 302)
        with patch("documentos.services.renderizar", side_effect=AssertionError("No debe regenerar")):
            self.assertEqual(self.client.get(respuesta.url).status_code, 200)
        self.assertEqual(GeneracionDocumento.objects.count(), 1)

    def test_sesion_expirada_no_genera(self):
        SessionActivity.objects.filter(session_id=self.client.session.session_key).update(
            last_activity=timezone.now() - timedelta(seconds=1801))
        respuesta = self.post_generacion()
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_tipo_inexistente_y_version_ausente_son_errores_controlados(self):
        self.assertEqual(self.client.get(self.url_revision("inexistente")).status_code, 404)
        self.assertEqual(self.client.post(self.url_revision(), {}).status_code, 200)
        self.assertFalse(GeneracionDocumento.objects.exists())
        with self.assertRaises(ValidationError):
            services.generar(concurso_id=self.concurso.pk, tipo_codigo="inexistente", usuario=self.operador,
                             version_concurso=1, version_destinatario=1)

    def test_configuracion_inicial_no_preselecciona_tratamiento_o_cargo(self):
        DestinatarioAPUNSJ.objects.all().delete()
        respuesta = self.client.get(reverse("documentos:configuracion_apunsj"))
        self.assertEqual(respuesta.status_code, 200)
        for campo in ("tratamiento", "cargo"):
            self.assertEqual(respuesta.context["form"].fields[campo].choices[0], ("", "Seleccioná una opción"))
            self.assertIsNone(respuesta.context["form"][campo].value())
        self.assertFalse(DestinatarioAPUNSJ.objects.exists())

    def test_datos_generales_faltantes_bloquean_oficio(self):
        Concurso.objects.filter(pk=self.concurso.pk).update(denominacion="")
        with self.assertRaises(ValidationError):
            self.generar()
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_permiso_generacion_sin_consulta_no_autoriza_acceso(self):
        usuario = get_user_model().objects.create_user("generador_sin_consulta", password=PASSWORD)
        usuario.user_permissions.add(Permission.objects.get(codename="generar_documento"))
        self.login(usuario)
        self.assertEqual(self.client.get(self.url_revision()).status_code, 403)
        with self.assertRaises(PermissionDenied):
            services.generar(concurso_id=self.concurso.pk, tipo_codigo="apunsj", usuario=usuario,
                             version_concurso=1, version_destinatario=1)

    def test_nueva_instancia_con_pk_existente_no_reemplaza_documento(self):
        original = self.generar()
        datos = {campo.attname: getattr(original, campo.attname)
                 for campo in original._meta.concrete_fields}
        datos["contenido"] = b"contenido adulterado"
        falso = GeneracionDocumento(**datos)
        with self.assertRaises(ValidationError):
            falso.save()
        conservado = GeneracionDocumento.objects.get(pk=original.pk)
        self.assertEqual(bytes(conservado.contenido), bytes(original.contenido))
        self.assertEqual(conservado.sha256, original.sha256)

    def test_caracteres_xml_invalidos_en_destinatario_o_concurso_son_error_controlado(self):
        for modelo, campo, pk in [(DestinatarioAPUNSJ, "nombre", self.destinatario.pk),
                                   (Concurso, "funciones", self.concurso.pk)]:
            for caracter in ("\x0b", "\x0c"):
                with self.subTest(modelo=modelo.__name__, caracter=repr(caracter)):
                    original = modelo.objects.values_list(campo, flat=True).get(pk=pk)
                    modelo.objects.filter(pk=pk).update(**{campo: f"Texto{caracter}prueba"})
                    with self.assertRaisesMessage(ValidationError, "caracteres de control"):
                        self.generar()
                    respuesta = self.post_generacion()
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertContains(respuesta, "caracteres de control")
                    self.assertFalse(GeneracionDocumento.objects.exists())
                    modelo.objects.filter(pk=pk).update(**{campo: original})

    def test_etiqueta_historial_y_navegacion_activa_compartida(self):
        self.generar()
        respuesta = self.client.get(self.concurso.get_absolute_url())
        self.assertEqual(respuesta.context["generaciones"][0].nombre_tipo, "Oficio a APUNSJ solicitando veedor")
        self.assertContains(respuesta, "Oficio a APUNSJ solicitando veedor")
        respuesta = self.client.get(self.url_revision())
        self.assertContains(respuesta, 'class="nav-link is-active" href="/concursos/" aria-current="page"')
        respuesta = self.client.get(reverse("documentos:configuracion"))
        self.assertContains(respuesta, 'class="nav-link is-active" href="/concursos/configuracion-institucional/" aria-current="page"')


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ContinuacionDocumentosTests(TestCase):
    """Regresiones de recuperación; datos exclusivamente ficticios."""

    setUpTestData = classmethod(DocumentosTests.setUpTestData.__func__)
    def setUp(self):
        DocumentosTests.setUp(self)
        self.jefatura = services.guardar_destinatario_personal(
            datos={"tratamiento": "Sra.", "cargo": "Jefa del Departamento de Personal",
                   "titulo": "Lic.", "nombre": "Persona", "apellido": "Ficticia"},
            usuario=self.operador, version_esperada=0)
        self.concurso.causa_vacancia = "nuevo"
        self.concurso.fecha_baja = timezone.localdate()
        # Un concurso correctamente identificado permite renderizar su estructura.
        self.concurso.jurisdiccion = "rectorado"
        self.concurso.save(update_fields=["causa_vacancia", "fecha_baja", "jurisdiccion"])

    login = DocumentosTests.login
    texto = DocumentosTests.texto
    huella = DocumentosTests.huella
    url_revision = DocumentosTests.url_revision

    def complementos(self, tipo):
        from .forms import COMPLEMENTOS
        datos = {nombre: f"Dato acreditado de prueba: {nombre}." for nombre, _, tipos, _ in COMPLEMENTOS if tipo in tipos}
        if tipo == "convocatoria":
            datos.update(fecha_apertura="2026-11-02")
        if tipo == "designacion":
            from .forms import PRESUPUESTO
            datos.update({f"presupuesto_{nombre}": "01" for nombre, _ in PRESUPUESTO})
        if tipo in ("dictamen", "designacion"):
            aspirantes = list(self.concurso.aspirantes.order_by("pk"))
            datos["merito"] = "\n".join(f"{i} | {a.pk}" for i, a in enumerate(reversed(aspirantes), 1))
        if tipo == "designacion":
            datos.update(aspirante_id=str(aspirantes[-1].pk), aplica_limitacion="no", limitacion="")
        return datos

    def test_elecciones_fuente_presente_genera_nota_editable(self):
        registro = services.generar(concurso_id=self.concurso.pk, tipo_codigo="elecciones", usuario=self.operador,
            version_concurso=self.concurso.version, complementarios=self.complementos("elecciones"), huella_esperada=self.huella("elecciones"))
        texto = self.texto(registro)
        self.assertIn("elección", texto)
        self.assertIn(self.concurso.expediente, texto)
        self.assertNotIn("PENDIENTE", texto)
        self.assertEqual(registro.plantilla_version, "elecciones-5")
        self.assertIn("Persona Ficticia", texto)
        self.assertIn("Acta Paritaria N.º 2/13", texto)
        self.assertIn("acto eleccionario deberá ser fiscalizado", texto)
        self.assertEqual(registro.instantanea["membrete"]["sha256"], self.membrete.sha256)

    def completar_fuentes(self, cantidad=4):
        from participantes.models import Persona, Jurado, Aspirante
        from expedientes.catalogo import POR_CODIGO
        for i, (representacion, calidad) in enumerate(
                (r, c) for r in Jurado.Representacion.values for c in Jurado.Calidad.values):
            persona = Persona.objects.create(nombre=f"Jurado ficticio {i}", apellido=f"Apellido J{i}",
                dni=f"1000000{i}", creado_por=self.operador, actualizado_por=self.operador)
            Jurado.objects.create(concurso=self.concurso, persona=persona, representacion=representacion,
                calidad=calidad, titulo="Título de prueba", unidad="Unidad de servicio de prueba",
                creado_por=self.operador, actualizado_por=self.operador)
        for i in range(cantidad):
            persona = Persona.objects.create(nombre=f"Aspirante ficticio {i}", apellido=f"Apellido A{i}",
                dni=f"2000000{i}", creado_por=self.operador, actualizado_por=self.operador)
            Aspirante.objects.create(concurso=self.concurso, persona=persona, creado_por=self.operador,
                                     actualizado_por=self.operador)
        for control in self.concurso.controles_documentales.all():
            control.verificado, control.responsable, control.verificado_en = True, self.operador, timezone.now()
            control.fojas = "5/8" if POR_CODIGO[control.requisito].requiere_foja else ""
            if control.requisito == "afectacion_presupuestaria":
                control.partida_principal = "03"
                control.actividad_presupuestaria = "04"
            control.save()
        self.concurso.turno_trabajo = "manana"
        self.concurso.domicilio_trabajo = "Calle Ficticia 123, San Juan"
        self.concurso.jurisdiccion = "rectorado"
        self.concurso.iniciador_nombre = "Persona iniciadora ficticia"
        self.concurso.iniciador_cargo = "Secretario de prueba"
        self.concurso.causa_vacancia = "nuevo"
        self.concurso.resolucion_convocatoria = "3278/26-R"
        self.concurso.save(update_fields=["turno_trabajo", "domicilio_trabajo", "jurisdiccion",
            "iniciador_nombre", "iniciador_cargo", "causa_vacancia", "resolucion_convocatoria"])

    def generar_tipo(self, tipo, datos=None, **kwargs):
        return services.generar(concurso_id=self.concurso.pk, tipo_codigo=tipo, usuario=self.operador,
            version_concurso=self.concurso.version, complementarios=datos if datos is not None else self.complementos(tipo),
            huella_esperada=kwargs.pop("huella_esperada", self.huella(tipo)), **kwargs)

    def test_cinco_salidas_con_fuentes_revisadas_sin_hechos_de_ejemplo(self):
        self.completar_fuentes(cantidad=7)
        for tipo in ("convocatoria", "dictamen", "designacion", "elecciones"):
            with self.subTest(tipo=tipo):
                registro = self.generar_tipo(tipo)
                texto = self.texto(registro)
                self.assertIn(self.concurso.expediente, texto)
                self.assertEqual(registro.instantanea["pendientes"], [])
                self.assertEqual(len(registro.instantanea["fuente"]["sha256"]), 64)
                self.assertEqual(registro.sha256, hashlib.sha256(bytes(registro.contenido)).hexdigest())
                for prohibido in ("{{", "3164/23", "11991", "unanimidad", "no se interpusieron", "soldadura", "PENDIENTE"):
                    self.assertNotIn(prohibido, texto)
                doc = Document(BytesIO(bytes(registro.contenido)))
                self.assertAlmostEqual(doc.sections[0].page_height.cm,
                                       27.94 if tipo == "elecciones" else 29.7, places=1)
                if tipo != "elecciones":
                    for encabezado in ("VISTO:", "CONSIDERANDO:", "RESUELVE:", "PROYECTO DE RESOLUCIÓN"):
                        self.assertIn(encabezado, texto)
                if tipo in ("dictamen", "designacion"):
                    self.assertEqual(len(registro.instantanea["aspirantes"]), 7)
                    for i in range(7):
                        self.assertIn(f"Aspirante ficticio {i}", texto)
                    orden = registro.instantanea["complementarios"]["orden_merito"]
                    self.assertEqual(orden[0]["aspirante_id"], self.concurso.aspirantes.order_by("pk").last().pk)
                if tipo in ("convocatoria", "designacion"):
                    self.assertEqual(len(doc.tables[-2].columns), 13)
                if tipo == "convocatoria":
                    self.assertEqual(len(doc.element.body.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr')), 12)
                    self.assertIn("ANEXO", texto)
                    self.assertIn("ARTÍCULO 8°", texto)

    def test_convocatoria_recupera_vacancia_e_iniciador_sin_reingreso_manual(self):
        self.completar_fuentes()
        from concursos import services as concurso_services
        datos = {**DATOS, "ex_titular": "Titular ficticio",
                 "fecha_baja": "2026-10-01", "motivo_baja": "Baja acreditada de prueba",
                 "resolucion_baja": "3278/26-R", "iniciador_tratamiento": "Sra.",
                 "causa_vacancia": "jubilacion", "jurisdiccion": "rectorado",
                 "turno_trabajo": "manana", "domicilio_trabajo": "Calle Ficticia 123, San Juan",
                 "iniciador_nombre": "Iniciadora ficticia", "iniciador_cargo": "Directora"}
        self.concurso = concurso_services.editar_concurso(pk=self.concurso.pk, datos=datos,
            usuario=self.operador, version_esperada=self.concurso.version)
        revision = self.client.get(self.url_revision("convocatoria"))
        self.assertEqual(revision.status_code, 200)
        self.assertNotIn("iniciador", revision.context["form"].fields)
        self.assertNotIn("antecedente_vacancia", revision.context["form"].fields)
        registro = self.generar_tipo("convocatoria")
        texto = self.texto(registro)
        self.assertIn("Iniciadora ficticia", texto)
        self.assertIn("Titular ficticio", texto)
        self.assertIn("3278/26-R", texto)
        self.assertEqual(registro.instantanea["concurso"]["fecha_baja"], "2026-10-01")

    def test_convocatoria_permite_funciones_vacias_y_omite_apartados_sin_contenido(self):
        """La ausencia de funciones no debe bloquear ni dejar una fila/ítem vacío."""
        from .registry import POR_CODIGO
        self.completar_fuentes()
        self.concurso.funciones = ""
        self.concurso.save(update_fields=["funciones"])
        estado = services.disponibilidad(self.concurso, POR_CODIGO["convocatoria"])
        self.assertTrue(estado["disponible"], estado["faltantes"])
        self.assertTrue(expediente_services.habilitacion_convocatoria(self.concurso).habilitado)

        registro = self.generar_tipo("convocatoria")
        texto = self.texto(registro)
        self.assertIn("ANEXO", texto)
        self.assertIn("FUNCIONES", texto)  # La denominación es el valor de este rótulo, siempre.
        self.assertIn(self.concurso.denominacion, texto)
        self.assertNotIn("No registradas", texto)
        documento = Document(BytesIO(bytes(registro.contenido)))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
        self.assertEqual(len(documento.element.body.findall(f".//{ns}")), 12)
        self.assertEqual(registro.instantanea["concurso"]["funciones"], "")

        self.concurso.funciones = "Funciones acreditadas de prueba"
        self.concurso.save(update_fields=["funciones"])
        registro_con_funciones = self.generar_tipo("convocatoria")
        texto_con_funciones = self.texto(registro_con_funciones)
        self.assertNotIn("Funciones acreditadas de prueba", texto_con_funciones)
        self.assertIn(self.concurso.denominacion, texto_con_funciones)
        self.assertEqual(len(Document(BytesIO(bytes(registro_con_funciones.contenido))).element.body.findall(f".//{ns}")), 12)

    def test_convocatoria_pie_limpio_articulos_al_margen_y_anexo_separado(self):
        self.completar_fuentes()
        registro = self.generar_tipo("convocatoria")
        documento = Document(BytesIO(bytes(registro.contenido)))

        self.assertEqual(documento.sections[0].footer.paragraphs[0].text, "")
        self.assertEqual(registro.plantilla_version, "convocatoria-7")
        articulos = [p for p in documento.paragraphs if p.text.startswith("ARTÍCULO ")]
        self.assertEqual(len(articulos), 8)
        for numero, parrafo_articulo in enumerate(articulos, 1):
            with self.subTest(articulo=numero):
                self.assertTrue(parrafo_articulo.text.startswith(f"ARTÍCULO {numero}°.-"))
                self.assertEqual(parrafo_articulo.paragraph_format.first_line_indent, Cm(0))
                self.assertEqual(parrafo_articulo.paragraph_format.left_indent, Cm(0))

        apartados = [p for p in documento.paragraphs
                     if p.style.name == "Sección anexo" and p._p.pPr is not None
                     and p._p.pPr.numPr is not None]
        self.assertEqual(len(apartados), 12)
        for apartado in apartados:
            self.assertEqual(apartado.paragraph_format.space_before, Pt(9))

    def test_otras_resoluciones_conservan_pie_y_sangria(self):
        self.completar_fuentes()
        registro = self.generar_tipo("dictamen")
        documento = Document(BytesIO(bytes(registro.contenido)))
        self.assertIn("BORRADOR NO EMITIDO", documento.sections[0].footer.paragraphs[0].text)
        articulo_dictamen = next(p for p in documento.paragraphs if p.text.startswith("ARTÍCULO "))
        self.assertIsNone(articulo_dictamen.paragraph_format.first_line_indent)

    def test_revision_convocatoria_agrupa_campos_sin_duplicarlos(self):
        from .forms import GRUPOS_CONVOCATORIA
        respuesta = self.client.get(self.url_revision("convocatoria"))
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["form"]
        en_grupos = [nombre for _, _, _, nombres in GRUPOS_CONVOCATORIA for nombre in nombres]
        self.assertEqual(en_grupos, ["fecha_apertura"])
        self.assertEqual(set(en_grupos), set(formulario.fields) - {
            "huella_esperada", "version_concurso", "version_destinatario", "revision_administrativa"})
        for nombre in en_grupos:
            self.assertContains(respuesta, f'name="{nombre}"', count=1)
        self.assertNotContains(respuesta, 'name="presupuesto_unidad"')
        for fragmento in ("Inscripciones", "control-documental", "Editar datos generales"):
            self.assertContains(respuesta, fragmento)
        self.assertNotContains(respuesta, "Inscripciones y consultas")

    def test_seis_notas_zip_bytes_y_descargas_individuales_historicas(self):
        self.completar_fuentes()
        datos = self.complementos("jurados")
        registro = self.generar_tipo("jurados", datos)
        with ZipFile(BytesIO(bytes(registro.contenido))) as archivo:
            self.assertEqual(archivo.namelist(), [f"jurado-{i}.docx" for i in range(1, 7)])
            miembros = {nombre: archivo.read(nombre) for nombre in archivo.namelist()}
        self.assertEqual(len(registro.instantanea["archivos"]), 6)
        with patch("documentos.services.renderizar", side_effect=AssertionError("No regenerar")):
            for fila in registro.instantanea["archivos"]:
                url = reverse("documentos:descargar_jurado", args=[self.concurso.pk, registro.pk, fila["indice"]])
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.content, miembros[fila["nombre"]])
                self.assertEqual(hashlib.sha256(respuesta.content).hexdigest(), fila["sha256"])
                doc = Document(BytesIO(respuesta.content))
                texto = "\n".join(p.text for p in doc.paragraphs)
                jurado = self.concurso.jurados.get(pk=fila["jurado_id"])
                self.assertIn(jurado.persona.nombre, texto)
                self.assertIn(jurado.calidad, texto)
                # Encabezado estricto: título y nombre, unidad, Presente.
                esperado = " ".join(v for v in (jurado.titulo.strip(),
                              jurado.persona.nombre, jurado.persona.apellido) if v)
                self.assertEqual([p.text for p in doc.paragraphs[1:4]],
                                 [esperado, jurado.unidad, "Presente"])
                self.assertIn("Correo electrónico:", texto)
                self.assertNotIn("Sin firma", texto)
                self.assertIn("Tengo el agrado de dirigirme a usted", texto)
                self.assertNotIn("DIRECCIÓN DE CONCURSOS NODOCENTES", texto)
                self.assertEqual(registro.instantanea["membrete"]["sha256"], self.membrete.sha256)
                self.assertIn("en las Ordenanzas N.º 33/10-CS y 20/11-CS", texto)
                self.assertIn("notificaciones correspondientes al desarrollo del concurso", texto)
                self.assertNotIn("Dato acreditado de prueba: marco_normativo", texto)
                self.assertIn("Firma:", texto)
                self.assertAlmostEqual(doc.sections[0].page_height.cm, 27.94, places=1)
        # No imprimir el tratamiento delante del destinatario: el encabezado
        # lleva título, nombre y apellido, seguido de la unidad y «Presente».
        self.assertNotIn("Tratamiento explícito", "\n".join(
            p.text for p in Document(BytesIO(miembros["jurado-1.docx"])).paragraphs[:4]))
        primero = self.concurso.jurados.order_by("pk").first()
        primero.persona.nombre = "Otro nombre posterior"
        primero.persona.save()
        respuesta = self.client.get(reverse("documentos:descargar", args=[self.concurso.pk, registro.pk]))
        self.assertEqual(respuesta.content, bytes(registro.contenido))
        self.assertEqual(respuesta["Content-Type"], "application/zip")
        self.assertEqual(self.client.get(reverse("documentos:descargar_jurado", args=[self.concurso.pk, registro.pk, 7])).status_code, 404)
        self.login(self.lector)
        self.assertEqual(self.client.get(reverse("documentos:descargar_jurado", args=[self.concurso.pk, registro.pk, 1])).status_code, 403)

    def test_notas_jurados_respetan_modelo_representacion_y_orden(self):
        self.completar_fuentes()
        datos = self.complementos("jurados")
        jurados = list(self.concurso.jurados.order_by("pk"))
        registro = self.generar_tipo("jurados", datos)
        self.assertEqual(registro.plantilla_version, "jurados-5")
        with ZipFile(BytesIO(bytes(registro.contenido))) as archivo:
            self.assertEqual(len(archivo.namelist()), 6)
            for fila in registro.instantanea["archivos"]:
                documento = Document(BytesIO(archivo.read(fila["nombre"])))
                texto = "\n".join(p.text for p in documento.paragraphs)
                self.assertIn("Tengo el agrado de dirigirme a usted", texto)
                self.assertIn("en carácter de", texto)
                self.assertIn("El mencionado concurso se sustancia", texto)
                self.assertIn("Asimismo, se solicita que tenga a bien informar", texto)
                self.assertIn("Sin otro particular, saludo a usted atentamente.", texto)
                self.assertNotIn("BORRADOR NO EMITIDO", documento.sections[0].footer.paragraphs[0].text)
                primer_parrafo = next(p for p in documento.paragraphs if p.text.startswith("Tengo el agrado"))
                negritas = "".join(r.text for r in primer_parrafo.runs if r.bold)
                self.assertIn(f'{fila["calidad"]}, en representación', negritas)
                for p in documento.paragraphs:
                    if p.text.startswith(("Firma:", "Aclaración:", "Fecha:", "Correo electrónico:")):
                        self.assertEqual(p.paragraph_format.line_spacing, 1.5)
                self.assertNotIn("{{", texto)
                if fila["representacion"] == "rectorado":
                    self.assertIn("en representación del Sr. Rector", texto)
                elif fila["representacion"] == "dependencia":
                    self.assertIn("en representación de la autoridad de la dependencia que convoca", texto)
                else:
                    self.assertIn("en representación del personal de la dependencia", texto)
                if fila["jurado_id"] == jurados[0].pk:
                    self.assertIn("ha sido designado/a", texto)
                self.assertAlmostEqual(documento.sections[0].page_height.cm, 27.94, places=1)

    def test_complementos_criticos_ausentes_no_generan_placeholders(self):
        self.completar_fuentes()
        for campo in ("fecha_apertura",):
            with self.subTest(campo=campo), self.assertRaises(ValidationError):
                self.generar_tipo("convocatoria", {**self.complementos("convocatoria"), campo: ""})
        for tipo in ("dictamen", "designacion"):
            datos = self.complementos(tipo)
            obligatorios = ("marco_normativo", "firmante", "lugar_fecha")
            for campo in obligatorios:
                with self.subTest(tipo=tipo, campo=campo), self.assertRaises(ValidationError):
                    self.generar_tipo(tipo, {**datos, campo: "   "})
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_convocatoria_solo_fecha_y_tabla_presupuestaria_fiel(self):
        self.completar_fuentes()
        registro = self.generar_tipo("convocatoria", {"fecha_apertura": "2026-11-02"})
        texto = self.texto(registro)
        self.assertIn("2 de noviembre de 2026", texto)
        self.assertIn("8 a 12", texto)
        self.assertIn("CINCO (5) días hábiles", texto)
        self.assertIn("7 a 14", texto)
        self.assertIn("Secretaría Administrativa Financiera", texto)
        self.assertIn("EL RECTOR DE LA UNIVERSIDAD NACIONAL DE SAN JUAN", texto)
        self.assertIn("Ordenanza 20/11-CS", texto)
        self.assertNotIn("Autoridad firmante propuesta", texto)
        self.assertNotIn("correo electrónico, indicado", texto)
        doc = Document(BytesIO(bytes(registro.contenido)))
        self.assertIn("03", [celda.text for fila in doc.tables[1].rows for celda in fila.cells])
        self.assertIn("04", [celda.text for fila in doc.tables[1].rows for celda in fila.cells])
        self.assertIn("1.1", [celda.text for fila in doc.tables[2].rows for celda in fila.cells])
        self.assertEqual(registro.instantanea["complementarios"]["fecha_apertura"], "2026-11-02")
        self.concurso.turno_trabajo = "tarde"
        self.concurso.save(update_fields=["turno_trabajo"])
        tarde = self.generar_tipo("convocatoria")
        self.assertIn("14 a 21", self.texto(tarde))

    def test_convocatoria_redaccion_aprobada_jurisdiccion_articulos_y_jurados(self):
        self.completar_fuentes()
        self.concurso.articulo_unidad = "el"
        self.concurso.articulo_dependencia = "la"
        self.concurso.articulo_superior = "la"
        self.concurso.articulo_iniciador = "el"
        self.concurso.save(update_fields=["articulo_unidad", "articulo_dependencia",
            "articulo_superior", "articulo_iniciador"])
        registro = self.generar_tipo("convocatoria")
        texto = self.texto(registro)
        self.assertIn("Que la Ordenanza N.º 33/10-CS", texto)
        self.assertIn("de actuaciones de referencia, se proponen los miembros", texto)
        self.assertIn("según documentación incorporada a fojas", texto)
        self.assertIn("del referido expediente", texto)
        self.assertIn("del mismo expediente, se adjunta la afectación presupuestaria", texto)
        self.assertIn("del mencionado expediente, según el siguiente detalle", texto)
        self.assertIn("dependiente de la", texto)
        self.assertIn("en el "+self.concurso.unidad, texto)
        self.assertIn("Dirección de Concursos Nodocentes", texto)
        self.assertIn("las y los postulantes", texto)
        self.assertIn("Título Secundario", texto)
        self.assertNotIn("TEMARIO ESPECÍFICO", texto)
        self.assertIn("Mantenimiento, producción y servicios generales - 03", texto)
        self.assertIn("EL RECTOR DE LA UNIVERSIDAD NACIONAL DE SAN JUAN", texto)
        self.assertIn("NÓMINA DE INTEGRANTES DEL JURADO", texto)
        self.assertLess(texto.index("En Representación del Rectorado"),
                        texto.index("En Representación de la Autoridad de la Dependencia que convoca"))
        self.assertLess(texto.index("En Representación de la Autoridad de la Dependencia que convoca"),
                        texto.index("En Representación del Personal de la Dependencia"))

    def test_articulos_reutilizables_con_preposiciones_y_contracciones(self):
        from .renderers import articulo_normalizado
        for articulo, pre, esperado in (
                ("el", "en", "en el"), ("la", "en", "en la"),
                ("del", "en", "en el"), ("de la", "en", "en la"),
                ("el", "de", "del"), ("la", "de", "de la"),
                ("del", "de", "del"), ("de la", "de", "de la"),
                ("", "de", "de"), ("", "en", "en")):
            with self.subTest(articulo=articulo, preposicion=pre):
                self.assertEqual(articulo_normalizado(articulo, pre), esperado)

    def test_convocatoria_causas_vacancia_no_presumidas(self):
        from .renderers import causa_de_vacancia
        self.completar_fuentes()
        base = services.instantanea_concurso(self.concurso)
        for causa, esperado in (("nuevo", "nueva creación"), ("fallecimiento", "fallecimiento"),
                                ("concurso", "otro cargo por concurso"), ("efectivizacion", "efectivización")):
            with self.subTest(causa=causa):
                dato = {**base, "causa_vacancia": causa, "ex_titular": "Persona ficticia",
                        "resolucion_baja": "1234/26-R"}
                texto = causa_de_vacancia({"concurso": dato})
                self.assertIn(esperado, texto)
                if causa != "nuevo":
                    self.assertNotIn("beneficio jubilatorio", texto)

    def test_convocatoria_requiere_datos_estructurales_sin_pedirlos_en_revision(self):
        from .registry import POR_CODIGO
        self.completar_fuentes()
        for campo, mensaje in (("jurisdiccion", "jurisdicción"),
                               ("domicilio_trabajo", "domicilio"),
                               ("causa_vacancia", "vacancia")):
            with self.subTest(campo=campo):
                original = getattr(self.concurso, campo)
                setattr(self.concurso, campo, "")
                resultado = services.disponibilidad(self.concurso, POR_CODIGO["convocatoria"])
                self.assertTrue(any(mensaje in m for m in resultado["faltantes"]))
                setattr(self.concurso, campo, original)

    def test_convocatoria_obliga_turno_y_codigos_si_faltan(self):
        self.completar_fuentes()
        from .registry import POR_CODIGO
        Concurso.objects.filter(pk=self.concurso.pk).update(turno_trabajo="")
        estado = services.disponibilidad(Concurso.objects.get(pk=self.concurso.pk), POR_CODIGO["convocatoria"])
        self.assertTrue(any("turno" in falta for falta in estado["faltantes"]))
        self.concurso.controles_documentales.filter(requisito="afectacion_presupuestaria").update(
            partida_principal="", actividad_presupuestaria="")
        estado = services.disponibilidad(Concurso.objects.get(pk=self.concurso.pk), POR_CODIGO["convocatoria"])
        self.assertTrue(any("PPAL" in falta for falta in estado["faltantes"]))
        self.assertTrue(any("actividad" in falta for falta in estado["faltantes"]))

    def test_merito_ajeno_duplicado_o_vacio_y_designacion_sin_eleccion_se_rechazan(self):
        self.completar_fuentes()
        a, b = self.concurso.aspirantes.order_by("pk")[:2]
        for tipo in ("dictamen", "designacion"):
            for merito in ("", f"1 | {a.pk}\n1 | {b.pk}", f"1 | {a.pk}\n2 | {a.pk}", "1 | 999999", f"2 | {a.pk}"):
                with self.subTest(tipo=tipo, merito=merito), self.assertRaises(ValidationError):
                    self.generar_tipo(tipo, {**self.complementos(tipo), "merito": merito})
        datos = self.complementos("designacion")
        for elegido in ("", "999999"):
            with self.assertRaises(ValidationError):
                self.generar_tipo("designacion", {**datos, "aspirante_id": elegido})
        with self.assertRaises(ValidationError):
            self.generar_tipo("designacion", {**datos, "aplica_limitacion": "si", "limitacion": ""})
        registro = self.generar_tipo("designacion", {**datos, "aplica_limitacion": "si", "limitacion": "Limitar designación anterior acreditada de prueba."})
        self.assertIn("ARTÍCULO 5°", self.texto(registro))

    def test_cambios_persona_jurado_aspirantes_controles_y_plantilla_invalidan_revision(self):
        self.completar_fuentes()
        from participantes.models import Jurado, Persona, Aspirante
        for modelo, campo in ((Persona, "nombre"), (Jurado, "unidad"), (Aspirante, "email")):
            objeto = self.concurso.jurados.order_by("pk").first().persona if modelo is Persona else modelo.objects.first()
            huella = self.huella("jurados" if modelo is not Aspirante else "dictamen")
            modelo.objects.filter(pk=objeto.pk).update(**{campo: "Cambio posterior"})
            with self.subTest(modelo=modelo.__name__), self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
                self.generar_tipo("jurados" if modelo is not Aspirante else "dictamen", huella_esperada=huella)
        huella = self.huella("convocatoria")
        self.concurso.controles_documentales.filter(requisito="vacancia").update(verificado=False)
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("convocatoria", huella_esperada=huella)
        huella = self.huella("elecciones")
        from .registry import POR_CODIGO
        from dataclasses import replace
        anterior = POR_CODIGO["elecciones"]
        # Debe cambiar efectivamente la versión; el catálogo ya puede estar
        # en elecciones-3 (o una versión posterior).
        with patch.dict(POR_CODIGO, elecciones=replace(anterior, version=f"{anterior.version}-prueba")):
            with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
                self.generar_tipo("elecciones", huella_esperada=huella)

    def test_antecedentes_y_codigos_presupuestarios_invalidan_revision_previa(self):
        self.completar_fuentes()
        huella = self.huella("convocatoria")
        Concurso.objects.filter(pk=self.concurso.pk).update(ex_titular="Ex titular de prueba")
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("convocatoria", huella_esperada=huella)
        huella = self.huella("convocatoria")
        self.concurso.controles_documentales.filter(requisito="afectacion_presupuestaria").update(
            partida_principal="01", actividad_presupuestaria="02")
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("convocatoria", huella_esperada=huella)

    def test_post_integrado_campos_requeridos_huella_y_permisos(self):
        self.completar_fuentes()
        for tipo in ("convocatoria", "jurados", "dictamen", "designacion", "elecciones"):
            with self.subTest(tipo=tipo):
                url = self.url_revision(tipo)
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                if tipo == "jurados":
                    self.assertContains(respuesta, "Generar seis notificaciones")
                    self.assertNotContains(respuesta, 'name="res_convocatoria"')
                    self.assertNotContains(respuesta, 'name="lugar_fecha"')
                elif tipo == "convocatoria":
                    self.assertContains(respuesta, 'name="fecha_apertura"')
                elif tipo in ("dictamen", "designacion"):
                    self.assertContains(respuesta, 'name="marco_normativo"')
                else:
                    self.assertNotContains(respuesta, 'name="marco_normativo"')
                datos = {**self.complementos(tipo), "version_concurso": self.concurso.version,
                         "version_destinatario": 1, "huella_esperada": respuesta.context["form"].initial["huella_esperada"]}
                self.assertEqual(self.client.post(url, {**datos, "huella_esperada": ""}).status_code, 200)
                respuesta = self.client.post(url, datos)
                self.assertEqual(respuesta.status_code, 302)
                self.assertEqual(self.client.get(respuesta.url).status_code, 200)
        self.assertEqual(GeneracionDocumento.objects.count(), 5)

    def test_convocatoria_y_antecedentes_incompletos_bloquean_sin_efectos(self):
        for tipo in ("convocatoria", "jurados", "dictamen", "designacion"):
            with self.subTest(tipo=tipo), self.assertRaises(ValidationError):
                self.generar_tipo(tipo, {})
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_acotado_exige_revision_y_marco_explicitos_sin_normas_ordinarias_inferidas(self):
        self.concurso.modalidad = "acotado"
        self.concurso.save()
        with self.assertRaises(ValidationError):
            self.generar_tipo("elecciones")
        # La nota fuente refiere a Cerrado Interno y al Acta 2/13.
        # Para Acotado se requiere otro modelo aprobado, no copiar éste.
        with self.assertRaisesMessage(ValidationError, "Cerrado Interno"):
            self.generar_tipo("elecciones", revision_administrativa=True)

    def test_generaciones_completas_no_modifican_procedimiento(self):
        self.completar_fuentes()
        antes = (list(self.concurso.controles_documentales.values()), list(self.concurso.historial.values()),
                 Concurso.objects.values().get(pk=self.concurso.pk), list(self.concurso.jurados.values()),
                 list(self.concurso.aspirantes.values()))
        for tipo in ("convocatoria", "jurados", "dictamen", "designacion", "elecciones"):
            self.generar_tipo(tipo)
        despues = (list(self.concurso.controles_documentales.values()), list(self.concurso.historial.values()),
                   Concurso.objects.values().get(pk=self.concurso.pk), list(self.concurso.jurados.values()),
                   list(self.concurso.aspirantes.values()))
        self.assertEqual(antes, despues)

    def test_notas_individuales_permisos_cruce_concurso_csrf_y_sesion(self):
        self.completar_fuentes()
        registro = self.generar_tipo("jurados")
        otro = concurso_services.crear_concurso(datos=DATOS, usuario=self.operador)
        self.assertEqual(self.client.get(reverse("documentos:descargar_jurado", args=[otro.pk, registro.pk, 1])).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        client.post(reverse("login"), {"username": self.operador.username, "password": PASSWORD,
                                       "csrfmiddlewaretoken": token})
        for tipo in ("convocatoria", "jurados", "dictamen", "designacion", "elecciones"):
            self.assertEqual(client.post(self.url_revision(tipo), {}).status_code, 403)
        SessionActivity.objects.filter(session_id=self.client.session.session_key).update(last_activity=timezone.now() - timedelta(seconds=1800))
        respuesta = self.client.get(reverse("documentos:descargar_jurado", args=[self.concurso.pk, registro.pk, 1]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)
        self.assertEqual(self.client.post(self.url_revision("jurados"), {}).status_code, 302)
        self.assertEqual(GeneracionDocumento.objects.count(), 1)

    def test_complemento_xml_invalido_y_fuente_cambiada_son_errores_controlados(self):
        self.completar_fuentes()
        DestinatarioPersonal.objects.filter(pk=1).update(nombre="Texto\x0bno válido")
        with self.assertRaisesMessage(ValidationError, "caracteres de control"):
            self.generar_tipo("elecciones")
        DestinatarioPersonal.objects.filter(pk=1).update(nombre="Persona")
        huella = self.huella("elecciones")
        from .registry import POR_CODIGO
        fuente = services.fuente_original(POR_CODIGO["elecciones"])
        lectura = type(fuente).read_bytes
        with patch.object(type(fuente), "read_bytes", lambda path: b"fuente modificada" if path == fuente else lectura(path)):
            with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
                self.generar_tipo("elecciones", huella_esperada=huella)
        self.assertFalse(GeneracionDocumento.objects.exists())



    def test_oficios_preparatorios_rechazan_jurisdiccion_ausente_sin_error_interno(self):
        self.concurso.jurisdiccion = ""
        self.concurso.save(update_fields=["jurisdiccion"])
        for tipo in ("elecciones",):
            with self.subTest(tipo=tipo):
                estado = services.disponibilidad(self.concurso, POR_CODIGO[tipo])
                self.assertFalse(estado["disponible"])
                self.assertTrue(any("jurisdicción" in faltante for faltante in estado["faltantes"]))
                with self.assertRaisesMessage(ValidationError, "jurisdicción"):
                    self.generar_tipo(tipo, {})
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_oficios_preparatorios_no_necesitan_resolucion_ni_jurados(self):
        self.assertFalse(self.concurso.jurados.exists())
        self.concurso.resolucion_convocatoria = ""
        self.concurso.save(update_fields=["resolucion_convocatoria"])
        for tipo in ("elecciones",):
            with self.subTest(tipo=tipo):
                registro = self.generar_tipo(tipo, {})
                documento = Document(BytesIO(bytes(registro.contenido)))
                texto = self.texto(registro)
                self.assertIn(self.concurso.expediente, texto)
                self.assertIn("Persona Ficticia", texto)
                self.assertIn("Jurado", texto)
                self.assertNotIn("BORRADOR NO EMITIDO", texto)
                self.assertEqual(registro.instantanea["membrete"]["sha256"], self.membrete.sha256)
                self.assertAlmostEqual(documento.sections[0].page_height.cm, 27.94, places=1)
                self.assertEqual(registro.instantanea["jurados"], [])
                # Las fechas, destinatarios, párrafos y firma deben mantener
                # una sola tipografía, incluso al abrir el DOCX en Word.
                for nombre in ("Normal", "Metadato institucional"):
                    self.assertEqual(documento.styles[nombre].font.name, "Arial")
                    self.assertEqual(documento.styles[nombre].font.size, Pt(11))
                for parrafo_oficio in documento.paragraphs:
                    for fragmento in parrafo_oficio.runs:
                        if fragmento.text:
                            self.assertEqual(fragmento.font.name, "Arial")
                            self.assertEqual(fragmento.font.size, Pt(11))
        self.assertFalse(self.concurso.controles_documentales.filter(verificado=True).exists())

    def test_jefatura_personal_permisos_concurrencia_y_cambio_de_autoridad(self):
        datos = {"tratamiento": "Sr.", "cargo": "Jefe del Departamento de Personal",
                 "titulo": "", "nombre": "Otro", "apellido": "Titular"}
        url = reverse("documentos:configuracion_personal")
        self.login(self.lector)
        self.assertEqual(self.client.get(url).status_code, 403)
        with self.assertRaises(PermissionDenied):
            services.guardar_destinatario_personal(datos=datos, usuario=self.lector, version_esperada=1)
        self.login(self.operador)
        historial = self.generar_tipo("elecciones", {})
        original = bytes(historial.contenido)
        services.guardar_destinatario_personal(datos=datos, usuario=self.operador, version_esperada=1)
        self.assertEqual(bytes(GeneracionDocumento.objects.get(pk=historial.pk).contenido), original)
        with self.assertRaisesMessage(ValidationError, "cambió"):
            services.guardar_destinatario_personal(datos=datos, usuario=self.operador, version_esperada=1)
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("elecciones", huella_esperada=historial.instantanea.get("revision_huella", "invalida"))

    def test_oficio_rectorado_retirado_sin_perder_descargas_historicas(self):
        from .registry import POR_CODIGO
        self.assertNotIn("solicitud_jurados_rectorado", POR_CODIGO)
        self.assertEqual(self.client.get(self.url_revision("solicitud_jurados_rectorado")).status_code, 404)
        with self.assertRaisesMessage(ValidationError, "Tipo de documento desconocido"):
            services.generar(concurso_id=self.concurso.pk, tipo_codigo="solicitud_jurados_rectorado",
                            usuario=self.operador, version_concurso=self.concurso.version)
        base = self.generar_tipo("elecciones", {})
        # Se conserva un registro del tipo retirado para verificar la ruta histórica.
        antiguo = GeneracionDocumento.objects.create(
            concurso=self.concurso, tipo="solicitud_jurados_rectorado",
            plantilla_version="jurados-rectorado-2", instantanea=base.instantanea,
            contenido=bytes(base.contenido), sha256=base.sha256, generado_por=self.operador)
        self.assertIn("Rector", antiguo.nombre_tipo)
        respuesta = self.client.get(reverse("documentos:descargar", args=[self.concurso.pk, antiguo.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.content, bytes(antiguo.contenido))
        ficha = self.client.get(self.concurso.get_absolute_url())
        self.assertNotContains(ficha, "Revisar oficio al Rector")
        self.assertContains(ficha, "Oficio al Rector solicitando jurados (histórico)")

    def test_membrete_institucional_permisos_archivo_validaciones_y_concurrencia(self):
        url = reverse("documentos:membrete")
        imagen_url = reverse("documentos:membrete_imagen")
        self.login(self.lector)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(imagen_url).status_code, 403)
        with self.assertRaises(PermissionDenied):
            services.guardar_membrete(
                imagen={"contenido": b"fake", "tipo_mime": "image/png", "nombre_archivo": "fake.png"},
                usuario=self.lector, version_esperada=1)
        self.login(self.configurador)
        self.assertEqual(self.client.get(url).status_code, 200)
        contenido = (Path(__file__).parent / "assets" / "unsj-crest-wordmark.png").read_bytes()
        archivo = SimpleUploadedFile("membrete-2027.png", contenido, content_type="image/png")
        respuesta = self.client.post(url, {"imagen": archivo, "version_esperada": 1})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(MembreteInstitucional.objects.get(pk=1).version, 2)
        self.assertEqual(self.client.get(imagen_url).content, contenido)
        archivo = SimpleUploadedFile("otra.png", contenido, content_type="image/png")
        respuesta = self.client.post(url, {"imagen": archivo, "version_esperada": 1})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "El membrete cambió")
        self.assertEqual(MembreteInstitucional.objects.get(pk=1).version, 2)
        for nombre, tipo, contenido_invalido in (("texto.txt", "text/plain", b"no es imagen"),
                                                  ("peligroso.svg", "image/svg+xml", b"<svg/>")):
            with self.subTest(nombre=nombre):
                archivo = SimpleUploadedFile(nombre, contenido_invalido, content_type=tipo)
                respuesta = self.client.post(url, {"imagen": archivo, "version_esperada": 2})
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "no es un PNG o JPG válido")

    def test_cambio_de_membrete_invalida_revision_y_preserva_zip_historico(self):
        self.completar_fuentes()
        primera_huella = self.huella("jurados")
        registro = self.generar_tipo("jurados", self.complementos("jurados"))
        antiguo_contenido = bytes(registro.contenido)
        antiguo_hash = registro.sha256
        imagen = (Path(__file__).parent / "assets" / "unsj-crest-wordmark.png").read_bytes()
        services.guardar_membrete(
            imagen={"contenido": imagen, "tipo_mime": "image/png", "nombre_archivo": "2027.png"},
            usuario=self.operador, version_esperada=1)
        self.assertNotEqual(primera_huella, self.huella("jurados"))
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("jurados", self.complementos("jurados"), huella_esperada=primera_huella)
        registro.refresh_from_db()
        self.assertEqual(bytes(registro.contenido), antiguo_contenido)
        self.assertEqual(registro.sha256, antiguo_hash)
        self.assertEqual(registro.instantanea["membrete"]["version"], 1)

    def test_jurados_reutilizan_resolucion_del_concurso_y_fecha_automatica(self):
        self.completar_fuentes()
        revision = self.client.get(self.url_revision("jurados"))
        self.assertEqual(revision.status_code, 200)
        campos = revision.context["form"].fields
        self.assertEqual(set(campos), {"huella_esperada", "version_concurso",
            "version_destinatario", "revision_administrativa"})
        self.assertContains(revision, "3278/26-R")
        self.assertNotContains(revision, 'name="tratamiento_')
        self.assertNotContains(revision, 'name="lugar_fecha"')
        # Aunque un cliente envíe datos heredados, se usan los del concurso y fecha del servidor.
        registro = self.generar_tipo("jurados", {"res_convocatoria": "9999/26-R",
            "lugar_fecha": "Fecha inventada", "tratamiento_1": "Sra."})
        self.assertEqual(registro.instantanea["complementarios"]["res_convocatoria"], "3278/26-R")
        self.assertIn("San Juan,", registro.instantanea["complementarios"]["lugar_fecha"])
        with ZipFile(BytesIO(bytes(registro.contenido))) as archivo:
            nota = Document(BytesIO(archivo.read("jurado-1.docx")))
        texto = "\n".join(p.text for p in nota.paragraphs)
        self.assertIn("3278/26-R", texto)
        self.assertNotIn("9999/26-R", texto)
        self.assertNotIn("Fecha inventada", texto)

        # Los números anteriores quedan en el archivo histórico; las nuevas versiones se invalidan.
        huella = self.huella("jurados")
        Concurso.objects.filter(pk=self.concurso.pk).update(resolucion_convocatoria="1234/26-R")
        with self.assertRaisesMessage(ValidationError, "Los datos cambiaron"):
            self.generar_tipo("jurados", huella_esperada=huella)
        registro.refresh_from_db()
        self.assertEqual(registro.instantanea["complementarios"]["res_convocatoria"], "3278/26-R")

    def test_jurados_bloquean_si_resolucion_no_esta_registrada(self):
        self.completar_fuentes()
        Concurso.objects.filter(pk=self.concurso.pk).update(resolucion_convocatoria="")
        actual = Concurso.objects.get(pk=self.concurso.pk)
        disponibilidad = services.disponibilidad(actual, POR_CODIGO["jurados"])
        self.assertFalse(disponibilidad["disponible"])
        self.assertTrue(any("resolución oficial de convocatoria" in x for x in disponibilidad["faltantes"]))
        with self.assertRaisesMessage(ValidationError, "resolución oficial de convocatoria"):
            self.generar_tipo("jurados", huella_esperada=self.huella("jurados"))

    def test_notificaciones_exigen_membrete_configurado(self):
        self.completar_fuentes()
        MembreteInstitucional.objects.all().delete()
        self.assertFalse(services.disponibilidad(self.concurso, POR_CODIGO["jurados"])["disponible"])
        with self.assertRaisesMessage(ValidationError, "Cargar el membrete vigente"):
            self.generar_tipo("jurados", self.complementos("jurados"), huella_esperada=self.huella("jurados"))
