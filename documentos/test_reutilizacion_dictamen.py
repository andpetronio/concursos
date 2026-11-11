"""Reutilización prudente del borrador de sorteo al preparar un dictamen."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from .forms import GeneracionForm
from .models import GeneracionDocumento
from .registry import POR_CODIGO
from .reutilizacion_dictamen import CAMPOS_ACTA_SORTEO, grupos_campos_dictamen


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReutilizacionDictamenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("reutilizacion_qa", password=PASSWORD)
        cls.usuario.user_permissions.set(Permission.objects.filter(
            content_type__app_label__in=("concursos", "documentos")))

    def setUp(self):
        self.concurso = crear_concurso(datos=DATOS, usuario=self.usuario)
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def nuevo_borrador(self, *, concurso=None, tipo="sorteo_acta", **complementarios):
        return GeneracionDocumento.objects.create(
            concurso=concurso or self.concurso,
            tipo=tipo, plantilla_version="prueba", instantanea={"complementarios": complementarios},
            contenido=b"docx-ficticio", sha256="0" * 64, generado_por=self.usuario,
        )

    def test_sin_acta_anterior_no_inventa_fechas_ni_autoridad(self):
        form = GeneracionForm(tipo=POR_CODIGO["dictamen"], concurso=self.concurso)
        self.assertEqual(form.sugerencias_dictamen, {})
        self.assertIsNone(form.origen_sugerencias_dictamen)
        self.assertIsNone(form["fecha_sorteo_tema"].value())
        self.assertIsNone(form["autoridad_nombre"].value())
        self.assertFalse(form["confirmar_unanimidad"].value())
        grupos = grupos_campos_dictamen(form)
        self.assertFalse(grupos["reutilizados"])
        self.assertTrue(grupos["pendientes"])
        self.assertTrue(grupos["confirmaciones"])

    def test_carga_ultimo_borrador_del_mismo_concurso_sin_marcar_confirmaciones(self):
        self.nuevo_borrador(fecha_sorteo_tema="2026-10-21", hora_sorteo_tema="09:30:00",
                           autoridad_nombre="Fiscalizadora anterior")
        esperado = self.nuevo_borrador(
            fecha_sorteo_tema="2026-10-29", hora_sorteo_tema="10:15:00",
            fecha_oposicion="2026-11-03", hora_oposicion="08:00:00",
            autoridad_tratamiento="Lic.", autoridad_cargo="Autoridad de prueba",
            autoridad_nombre="Fiscalizadora actual",
            confirmar_unanimidad="on",  # Nunca se copia una declaración.
        )
        form = GeneracionForm(tipo=POR_CODIGO["dictamen"], concurso=self.concurso)
        self.assertEqual(form.origen_sugerencias_dictamen.pk, esperado.pk)
        self.assertEqual(set(form.sugerencias_dictamen), set(CAMPOS_ACTA_SORTEO))
        self.assertEqual(form["hora_sorteo_tema"].value(), "10:15")
        self.assertEqual(form["fecha_oposicion"].value(), "2026-11-03")
        self.assertEqual(form["autoridad_nombre"].value(), "Fiscalizadora actual")
        self.assertFalse(form["confirmar_unanimidad"].value())
        self.assertFalse(form["confirmar_notificacion"].value())
        grupos = grupos_campos_dictamen(form)
        self.assertEqual(len(grupos["reutilizados"]), len(CAMPOS_ACTA_SORTEO))
        self.assertTrue(any(c.name == "confirmar_notificacion" for c in grupos["confirmaciones"]))

    def test_no_mezcla_otros_concursos_ni_otros_documentos(self):
        otro = crear_concurso(datos={**DATOS, "expediente": "01-987-2026"}, usuario=self.usuario)
        self.nuevo_borrador(concurso=otro, fecha_sorteo_tema="2026-10-29")
        self.nuevo_borrador(tipo="dictamen", fecha_sorteo_tema="2026-10-28")
        form = GeneracionForm(tipo=POR_CODIGO["dictamen"], concurso=self.concurso)
        self.assertEqual(form.sugerencias_dictamen, {})
        self.assertIsNone(form["fecha_sorteo_tema"].value())

    def test_valores_invalidos_de_snapshot_no_se_proponen(self):
        self.nuevo_borrador(fecha_sorteo_tema="ayer", hora_oposicion="sin hora",
                           autoridad_nombre={"inesperado": "dato"},
                           autoridad_cargo="Autoridad legible")
        form = GeneracionForm(tipo=POR_CODIGO["dictamen"], concurso=self.concurso)
        self.assertEqual(form.sugerencias_dictamen, {"autoridad_cargo": "Autoridad legible"})
        self.assertIsNone(form["fecha_sorteo_tema"].value())

    def test_post_no_rellena_campos_ausentes_con_valores_historicos(self):
        self.nuevo_borrador(fecha_sorteo_tema="2026-10-29", autoridad_nombre="Histórica")
        form = GeneracionForm(data={"fecha_sorteo_tema": "2026-11-02",
                                   "autoridad_nombre": "Corregida"},
                              tipo=POR_CODIGO["dictamen"], concurso=self.concurso)
        self.assertEqual(form["fecha_sorteo_tema"].value(), "2026-11-02")
        self.assertEqual(form["autoridad_nombre"].value(), "Corregida")
        self.assertIsNone(form["hora_sorteo_tema"].value())
        self.assertFalse(form.is_valid())
        self.assertIn("confirmar_notificacion", form.errors)

    def test_revision_clasica_presenta_origen_y_grupos_sin_repetir_campos(self):
        origen = self.nuevo_borrador(fecha_sorteo_tema="2026-10-29", hora_sorteo_tema="09:30:00",
                                    autoridad_nombre="Fiscalizadora")
        response = self.client.get(reverse("documentos:revisar", args=(self.concurso.pk, "dictamen")))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Datos que SiCon ya incorpora")
        self.assertContains(response, "Datos propuestos desde un borrador anterior")
        self.assertContains(response, f"registro N.º {origen.pk}")
        self.assertContains(response, "Datos que faltan completar o revisar")
        self.assertContains(response, "Constancias que debés confirmar")
        self.assertContains(response, 'value="2026-10-29"')
        self.assertContains(response, 'value="09:30"')
        self.assertContains(response, 'value="Fiscalizadora"')
        for campo in response.context["form"].visible_fields():
            self.assertContains(response, f'name="{campo.name}"', count=1)

    def test_contexto_embebido_utiliza_la_misma_clasificacion(self):
        from . import services
        self.nuevo_borrador(fecha_sorteo_tema="2026-10-29", autoridad_nombre="Fiscalizadora")
        # La ficha habilita un formulario al estar la documentación completa.
        # En esta prueba forzamos solo la presentación de errores, sin inventar checks.
        form = GeneracionForm(data={"dictamen-autoridad_nombre": "Rectificada"},
                              prefix="dictamen", tipo=POR_CODIGO["dictamen"],
                              concurso=self.concurso)
        datos = services.contexto_documentos(self.concurso, usuario=self.usuario,
                                            formulario_error_tipo="dictamen",
                                            formulario_error=form)
        doc = next(d for d in datos["tipos_documentos"] if d["tipo"].codigo == "dictamen")
        grupos = doc["grupos_dictamen"]
        self.assertEqual([c.name for c in grupos["reutilizados"]],
                         ["fecha_sorteo_tema", "autoridad_nombre"])
        self.assertEqual(form["autoridad_nombre"].value(), "Rectificada")
        self.assertTrue(any(c.name == "confirmar_unanimidad" for c in grupos["confirmaciones"]))

    def test_las_otras_plantillas_no_toman_datos_de_sorteo(self):
        self.nuevo_borrador(fecha_sorteo_tema="2026-10-29")
        for codigo in ("sorteo_acta", "designacion"):
            with self.subTest(tipo=codigo):
                form = GeneracionForm(tipo=POR_CODIGO[codigo], concurso=self.concurso)
                self.assertNotIn("fecha_sorteo_tema", form.initial)
