"""F4M.3: los cambios del jurado pasan al DOCX solo si están acreditados."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from docx import Document

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from participantes.jurados_services import registrar_presentacion, resolver_presentacion
from participantes.models import ActuacionJurado, Jurado, Persona

from .forms import GeneracionForm
from .jurados_integracion import incorporar_antecedentes_jurado
from .registry import POR_CODIGO
from .renderers import antecedentes_posteriores
from .services import fuentes_actuales, huella_fuentes


class ConsiderandosEnGeneracionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operador = get_user_model().objects.create_user(username="f4m3_operador")
        cls.operador.user_permissions.set(
            Permission.objects.filter(content_type__app_label="concursos")
        )
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.operador)
        cls.jurados = []
        for i, (nombre, apellido, calidad) in enumerate((
            ("Juan", "Pérez", "titular"), ("María", "Gómez", "suplente"),
        )):
            persona = Persona.objects.create(
                nombre=nombre, apellido=apellido, dni=f"3456010{i}",
                creado_por=cls.operador, actualizado_por=cls.operador,
            )
            cls.jurados.append(Jurado.todos.create(
                concurso=cls.concurso, persona=persona,
                representacion="rectorado", calidad=calidad, titulo="Licenciado",
                unidad="Rectorado", creado_por=cls.operador,
                actualizado_por=cls.operador,
            ))

    def registrar_cambio(self, *, fojas="48/49"):
        titular = self.jurados[0]
        presentacion = registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            usuario=self.operador, version_esperada=titular.version,
            motivo="excusacion", fecha_actuacion=date(2026, 10, 20), fojas="45",
        )
        resolver_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            presentacion_id=presentacion.pk, usuario=self.operador,
            version_esperada=titular.version, resolucion="3278/26-R",
            fecha_resolucion=date(2026, 10, 30), fojas=fojas,
            promover_suplente=True,
        )

    def test_cese_y_promocion_se_incorporan_sin_duplicaciones(self):
        self.registrar_cambio()
        datos = incorporar_antecedentes_jurado(
            concurso=self.concurso, fecha_corte=date(2026, 11, 2),
        )
        self.assertEqual(len(datos["resoluciones"]), 1)
        self.assertEqual(len(datos["textos"]), 3)
        self.assertEqual(datos["resoluciones"][0]["numero"], "3278/26-R")
        self.assertIn("Juan Pérez", " ".join(datos["textos"]))
        self.assertIn("María Gómez", " ".join(datos["textos"]))
        self.assertTrue(datos["revision_explicita"])

    def test_faltan_fojas_impide_omitir_silenciosamente_resolucion(self):
        self.registrar_cambio(fojas="")
        with self.assertRaisesMessage(ValidationError, "Fojas de la resolución rectoral"):
            incorporar_antecedentes_jurado(
                concurso=self.concurso, fecha_corte=date(2026, 11, 2),
            )

    def test_fecha_historica_se_bloquea_para_no_usar_jurado_actual(self):
        self.registrar_cambio()
        with self.assertRaisesMessage(ValidationError, "composición actual"):
            incorporar_antecedentes_jurado(
                concurso=self.concurso, fecha_corte=date(2026, 10, 25),
            )

    def test_presentacion_pendiente_no_genera_considerando_de_cese(self):
        titular = self.jurados[0]
        registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            usuario=self.operador, version_esperada=titular.version,
            motivo="recusacion", fecha_actuacion=date(2026, 10, 25), fojas="15",
        )
        datos = incorporar_antecedentes_jurado(
            concurso=self.concurso, fecha_corte=date(2026, 11, 2),
        )
        self.assertEqual(datos["textos"], [])
        self.assertTrue(any("pendiente" in av for av in datos["advertencias"]))

    def test_una_actuacion_modifica_la_huella_del_borrador(self):
        tipo = POR_CODIGO["dictamen"]
        anterior = huella_fuentes(fuentes_actuales(self.concurso, tipo)[0])
        self.registrar_cambio()
        posterior = huella_fuentes(fuentes_actuales(self.concurso, tipo)[0])
        self.assertNotEqual(anterior, posterior)

    def test_campos_de_revision_solo_con_actuaciones(self):
        for codigo in ("dictamen", "designacion"):
            form = GeneracionForm(tipo=POR_CODIGO[codigo], concurso=self.concurso)
            self.assertNotIn("fecha_corte_jurado", form.fields)
            self.assertNotIn("confirmacion_jurado", form.fields)
        titular = self.jurados[0]
        registrar_presentacion(
            jurado_id=titular.pk, concurso_id=self.concurso.pk,
            usuario=self.operador, version_esperada=titular.version,
            motivo="excusacion", fecha_actuacion=date(2026, 10, 25), fojas="15",
        )
        for codigo in ("dictamen", "designacion"):
            form = GeneracionForm(tipo=POR_CODIGO[codigo], concurso=self.concurso)
            self.assertIn("fecha_corte_jurado", form.fields)
            self.assertTrue(form.fields["fecha_corte_jurado"].required)
            self.assertIn("confirmacion_jurado", form.fields)
            self.assertTrue(form.fields["confirmacion_jurado"].required)

    def test_insercion_word_sin_alterar_considerandos_previos(self):
        documento = Document()
        datos = {
            "complementarios": {
                "res_convocatoria": "3000/26-R", "antecedentes_inscriptos": "Consta.",
                "valoracion": "Consta.", "sorteo": "Consta.",
                "prueba": "Consta.", "resultado": "Consta.",
                "impugnaciones": "Que no hubo impugnaciones.",
                "comunicacion": "Que se notificó.", "tramites": "Que se cumplieron los trámites.",
            },
            "aspirantes": [],
            "considerandos_jurado": {"textos": [
                "Que Juan Pérez formuló una excusación;",
                "Que por Resolución 3278/26-R fue aceptada;",
            ]},
        }
        with patch("documentos.renderers.jurados_texto", return_value="Jurados actuales"), \
             patch("documentos.renderers.foja", return_value="45"):
            antecedentes_posteriores(documento, datos)
        parrafos = [p.text for p in documento.paragraphs]
        pos = parrafos.index("Integración del jurado: Jurados actuales.")
        self.assertEqual(parrafos[pos+1:pos+3], datos["considerandos_jurado"]["textos"])
        self.assertIn("Que no hubo impugnaciones.", parrafos)

    def test_antecedentes_previos_sin_actuaciones_no_agregan_textos(self):
        documento = Document()
        datos = {
            "complementarios": {
                "res_convocatoria": "3000/26-R", "antecedentes_inscriptos": "Consta.",
                "valoracion": "Consta.", "sorteo": "Consta.",
                "prueba": "Consta.", "resultado": "Consta.",
                "impugnaciones": "", "comunicacion": "", "tramites": "",
            },
            "aspirantes": [],
        }
        with patch("documentos.renderers.jurados_texto", return_value="Jurados actuales"), \
             patch("documentos.renderers.foja", return_value="45"):
            antecedentes_posteriores(documento, datos)
        texto = " ".join(p.text for p in documento.paragraphs)
        self.assertNotIn("3278/26-R", texto)
