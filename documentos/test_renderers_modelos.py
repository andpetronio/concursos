"""Regresiones del reemplazo de variables en modelos Word institucionales."""

from django.test import SimpleTestCase
from docx import Document

from .renderers_modelos import _reemplazar


class ReemplazoModelosWordTests(SimpleTestCase):
    def test_ignora_sustitucion_identica_sin_bucle(self):
        documento = Document()
        parrafo = documento.add_paragraph('Tramo Inicial, Agrupamiento Administrativo 01.')
        _reemplazar(parrafo, {
            'Tramo Inicial': 'Tramo Inicial',
            'Administrativo 01': 'Administrativo 01',
        })
        self.assertEqual(parrafo.text, 'Tramo Inicial, Agrupamiento Administrativo 01.')

    def test_reemplazo_que_contiene_el_original_se_procesa_una_vez(self):
        documento = Document()
        parrafo = documento.add_paragraph('Resolución 3164/23-R.')
        _reemplazar(parrafo, {'3164/23-R': 'Antecedente 3164/23-R'})
        self.assertEqual(parrafo.text, 'Resolución Antecedente 3164/23-R.')

    def test_sustituye_todas_las_ocurrencias_incluso_entre_runs(self):
        documento = Document()
        parrafo = documento.add_paragraph()
        parrafo.add_run('El {{nom')
        parrafo.add_run('bre}} y {{nombre}}').bold = True
        _reemplazar(parrafo, {'{{nombre}}': 'Pérez'})
        self.assertEqual(parrafo.text, 'El Pérez y Pérez')
