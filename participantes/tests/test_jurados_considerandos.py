"""F4M.1: el borrador debe expresar solamente hechos registrados en F4L."""
from datetime import date
from types import SimpleNamespace as Dato
from unittest import TestCase

from participantes.jurados_considerandos import preparar_antecedentes_jurado


def persona(nombre, apellido):
    return Dato(persona=Dato(nombre=nombre, apellido=apellido))


def acto(pk, tipo, jurado, fecha, resolucion="", fojas="", antecedente=None,
         representacion="rectorado", motivo="", calidad_anterior="", calidad_nueva="",
         resuelto_por=None):
    return Dato(pk=pk, tipo=tipo, jurado=jurado, fecha_actuacion=fecha,
                resolucion=resolucion, fojas=fojas, antecedente=antecedente,
                antecedente_id=getattr(antecedente, "pk", None),
                representacion=representacion, motivo=motivo,
                calidad_anterior=calidad_anterior, calidad_nueva=calidad_nueva,
                resuelto_por=resuelto_por)


class ConsiderandosJuradoTests(TestCase):
    def setUp(self):
        self.original = persona("Juan", "Pérez")
        self.suplente = persona("María", "Gómez")
        self.presentacion = acto(1, "presentacion", self.original, date(2026, 10, 20),
                                 fojas="45", motivo="excusacion", calidad_anterior="titular")
        self.cese = acto(2, "cese", self.original, date(2026, 10, 30), "3278/26-R", "48/49",
                         self.presentacion, motivo="excusacion", calidad_anterior="titular")
        self.presentacion.resuelto_por = self.cese
        self.promocion = acto(3, "promocion", self.suplente, date(2026, 10, 30),
                              "3278/26-R", "48/49", self.presentacion,
                              calidad_anterior="suplente", calidad_nueva="titular")

    def test_sin_modificaciones_no_se_inventan_considerandos(self):
        vista = preparar_antecedentes_jurado([])
        self.assertEqual(vista.bloques, ())
        self.assertTrue(vista.completa_para_revision)

    def test_cese_y_promocion_misma_resolucion_se_agrupan(self):
        vista = preparar_antecedentes_jurado([self.promocion, self.presentacion, self.cese])
        self.assertEqual(len(vista.bloques), 1)
        bloque = vista.bloques[0]
        self.assertEqual(bloque.identificadores_actuacion, (2, 3))
        self.assertEqual(len(bloque.considerandos), 3)
        texto = " ".join(bloque.considerandos)
        for esperado in ("Juan Pérez", "María Gómez", "3278/26-R", "45", "48/49"):
            self.assertIn(esperado, texto)
        self.assertTrue(vista.completa_para_revision)

    def test_sin_fojas_no_inventa_datos_ni_emite_considerandos(self):
        self.cese.fojas = ""
        vista = preparar_antecedentes_jurado([self.cese, self.promocion])
        self.assertEqual(vista.bloques[0].considerandos, ())
        self.assertIn("Fojas de la resolución rectoral", vista.bloques[0].faltantes)
        self.assertFalse(vista.completa_para_revision)

    def test_presentacion_pendiente_no_equivale_a_cese(self):
        self.presentacion.resuelto_por = None
        vista = preparar_antecedentes_jurado([self.presentacion])
        self.assertEqual(vista.bloques, ())
        self.assertEqual(len(vista.advertencias), 1)
        self.assertIn("pendiente", vista.advertencias[0])

    def test_recusacion_no_atribuye_su_presentacion_al_jurado(self):
        self.presentacion.motivo = "recusacion"
        self.cese.motivo = "recusacion"
        vista = preparar_antecedentes_jurado([self.cese])
        texto = " ".join(vista.bloques[0].considerandos)
        self.assertIn("recusación respecto de Juan Pérez", texto)
        self.assertNotIn("formulada por Juan Pérez", texto)

    def test_filtro_fecha_documento_omite_actos_posteriores(self):
        vista = preparar_antecedentes_jurado([self.cese, self.promocion],
                                              fecha_documento=date(2026, 10, 25))
        self.assertEqual(vista.bloques, ())

    def test_designacion_nuevo_suplente_es_bloque_independiente(self):
        designacion = acto(4, "designacion", persona("Pedro", "Ríos"),
                           date(2026, 11, 1), "3380/26-R", "60/61", calidad_nueva="suplente")
        vista = preparar_antecedentes_jurado([designacion, self.cese, self.promocion])
        self.assertEqual([x.resolucion for x in vista.bloques], ["3278/26-R", "3380/26-R"])
        self.assertIn("Pedro Ríos", vista.bloques[1].considerandos[0])

    def test_promocion_sin_cese_no_se_presenta_como_hecho_acreditado(self):
        vista = preparar_antecedentes_jurado([self.promocion])
        self.assertEqual(vista.bloques, ())
        self.assertIn("sin cese vinculado", vista.advertencias[0])

    def test_fechas_incoherentes_bloquean_borrador(self):
        self.presentacion.fecha_actuacion = date(2026, 11, 10)
        vista = preparar_antecedentes_jurado([self.cese])
        self.assertFalse(vista.bloques[0].completo_para_revision)
        self.assertIn("posterior", " ".join(vista.bloques[0].faltantes))
