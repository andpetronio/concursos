"""Proyecto de dictamen con situaciones individuales documentadas (datos ficticios)."""
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from docx import Document
from io import BytesIO

from participantes.models import Aspirante, CambioSituacionAspirante, Persona
from participantes.situaciones import registrar_actuacion
from . import services
from .forms import GeneracionForm
from .models import GeneracionDocumento
from .registry import POR_CODIGO
from .tests import DocumentosTests, ContinuacionDocumentosTests


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DictamenConActuacionesTests(TestCase):
    setUpTestData = classmethod(DocumentosTests.setUpTestData.__func__)
    login = DocumentosTests.login
    huella = DocumentosTests.huella
    texto = DocumentosTests.texto
    completar_fuentes = ContinuacionDocumentosTests.completar_fuentes
    complementos = ContinuacionDocumentosTests.complementos
    generar_tipo = ContinuacionDocumentosTests.generar_tipo

    def setUp(self):
        ContinuacionDocumentosTests.setUp(self)
        self.completar_fuentes(cantidad=1)
        self.habilitado = self.concurso.aspirantes.get()
        persona = Persona.objects.create(
            nombre='Persona sin evaluación', apellido='Actuación de prueba',
            dni='29999111', creado_por=self.operador, actualizado_por=self.operador,
        )
        # Esta inscripción nunca tuvo evaluación: no fabricar ni borrar puntajes.
        self.no_continua = Aspirante.objects.create(
            concurso=self.concurso, persona=persona,
            creado_por=self.operador, actualizado_por=self.operador,
        )

    def actuacion(self, tipo='no_habilitacion', clase='acta', documento='Acta del Jurado Nº 14/26'):
        return registrar_actuacion(
            aspirante=self.no_continua, tipo=tipo, usuario=self.operador,
            fecha_decision=date(2026, 11, 4), clase_documento=clase,
            documento=documento, fojas='45/47',
            fundamento='Fundamentos documentados en la actuación ficticia.',
            version_esperada=self.no_continua.version,
        )

    def datos(self):
        return {**self.complementos('dictamen'), 'confirmar_situaciones_individuales': True}

    def test_no_habilitado_documentado_no_requiere_puntajes_y_figura_en_considerandos(self):
        self.actuacion()
        estado = services.disponibilidad(self.concurso, POR_CODIGO['dictamen'])
        self.assertTrue(estado['disponible'], estado['faltantes'])
        registro = self.generar_tipo('dictamen', self.datos())
        texto = self.texto(registro)
        nombre = self.no_continua.persona.nombre
        self.assertIn('VARIANTE CON ACTUACIONES INDIVIDUALES', texto)
        self.assertIn('no quedó habilitado para participar en la prueba de oposición', texto)
        self.assertIn('Acta del Jurado Nº 14/26', texto)
        self.assertIn('45/47', texto)
        self.assertIn(nombre, texto)
        self.assertNotIn('no han sido interpuestas impugnaciones', texto)
        self.assertIn('en presencia de los aspirantes que participaron del sorteo', texto)
        self.assertEqual(registro.plantilla_version, 'dictamen-fuente-2')
        self.assertEqual(registro.instantanea['resultados']['evaluaciones_pendientes'], [])
        self.assertEqual(len(registro.instantanea['resultados']['orden_merito']), 1)
        self.assertEqual(registro.instantanea['resultados']['orden_merito'][0]['aspirante_id'], self.habilitado.pk)
        self.assertEqual(registro.instantanea['resultados']['cantidad_aspirantes'], 2)
        self.assertEqual(registro.instantanea['resultados']['cantidad_habilitados'], 1)
        self.assertEqual(len(registro.instantanea['actuaciones_aspirantes']), 1)
        self.assertEqual(registro.instantanea['actuaciones_aspirantes'][0]['fojas'], '45/47')
        self.assertEqual(GeneracionDocumento.objects.count(), 1)
        # Word sigue siendo editable y no deja variables de plantilla pendientes.
        doc = Document(BytesIO(bytes(registro.contenido)))
        self.assertNotIn('{{', '\n'.join(p.text for p in doc.paragraphs))

    def test_exclusion_por_resolucion_no_afirma_ausencia_de_impugnaciones(self):
        self.actuacion('exclusion', 'resolucion', 'Resolución 1988/26-R')
        self.assertTrue(services.disponibilidad(self.concurso, POR_CODIGO['dictamen'])['disponible'])
        form = GeneracionForm(tipo=POR_CODIGO['dictamen'], concurso=self.concurso)
        self.assertNotIn('confirmar_sin_impugnaciones', form.fields)
        self.assertIn('confirmar_situaciones_individuales', form.fields)
        texto = self.texto(self.generar_tipo('dictamen', self.datos()))
        self.assertIn('se dispuso la exclusión', texto)
        self.assertIn('Resolución 1988/26-R', texto)
        self.assertNotIn('no han sido interpuestas impugnaciones', texto)

    def test_desistimiento_documentado_puede_reflejarse_sin_evaluacion(self):
        self.actuacion('desistimiento', 'nota', 'Nota de desistimiento Nº 3/26')
        texto = self.texto(self.generar_tipo('dictamen', self.datos()))
        self.assertIn('se dejó constancia del desistimiento', texto)
        self.assertIn('Nota de desistimiento Nº 3/26', texto)

    def test_situacion_sin_respaldo_valido_bloquea_y_no_emite(self):
        Aspirante.objects.filter(pk=self.no_continua.pk).update(situacion='no_habilitado', version=2)
        faltantes = services.disponibilidad(self.concurso, POR_CODIGO['dictamen'])['faltantes']
        self.assertTrue(any('actuación que respalda' in f for f in faltantes))
        with self.assertRaisesMessage(ValidationError, 'actuación que respalda'):
            self.generar_tipo('dictamen', self.datos())
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_edicion_posterior_de_datos_del_aspirante_no_invalida_la_actuacion(self):
        self.actuacion()
        # El historial de situación no se reescribe al corregir un dato personal.
        Aspirante.objects.filter(pk=self.no_continua.pk).update(version=3)
        estado = services.disponibilidad(self.concurso, POR_CODIGO['dictamen'])
        self.assertTrue(estado['disponible'], estado['faltantes'])
        self.assertIn('no quedó habilitado', self.texto(self.generar_tipo('dictamen', self.datos())))

    def test_impugnacion_pendiente_sigue_bloqueando(self):
        self.actuacion('impugnacion', 'nota', 'Presentación Nº 5/26')
        faltantes = services.disponibilidad(self.concurso, POR_CODIGO['dictamen'])['faltantes']
        self.assertTrue(any('Impugnación pendiente' in f for f in faltantes))
        with self.assertRaisesMessage(ValidationError, 'Impugnación pendiente'):
            self.generar_tipo('dictamen', self.datos())
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_sin_confirmacion_administrativa_no_se_genera_documento(self):
        self.actuacion()
        with self.assertRaisesMessage(ValidationError, 'confirmar_situaciones_individuales'):
            self.generar_tipo('dictamen', self.complementos('dictamen'))
        self.assertFalse(GeneracionDocumento.objects.exists())

    def test_cambio_de_actuacion_invalida_huella_y_preserva_documento_historico(self):
        self.actuacion()
        huella = self.huella('dictamen')
        registro = self.generar_tipo('dictamen', self.datos())
        bytes_guardados = bytes(registro.contenido)
        sha_guardado = registro.sha256
        CambioSituacionAspirante.objects.filter(aspirante=self.no_continua).update(fojas='51/52')
        self.assertNotEqual(self.huella('dictamen'), huella)
        with self.assertRaisesMessage(ValidationError, 'Los datos cambiaron'):
            self.generar_tipo('dictamen', self.datos(), huella_esperada=huella)
        registro.refresh_from_db()
        self.assertEqual(bytes(registro.contenido), bytes_guardados)
        self.assertEqual(registro.sha256, sha_guardado)

    def test_designacion_sigue_bloqueada_hasta_su_variante_propia(self):
        self.actuacion()
        faltantes = services.disponibilidad(self.concurso, POR_CODIGO['designacion'])['faltantes']
        self.assertTrue(any('variante del proyecto de designación' in falta for falta in faltantes))
