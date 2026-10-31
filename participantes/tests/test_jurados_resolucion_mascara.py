"""F4L.7: máscara y validación del número rectoral en ambos formularios."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.fields import ResolucionRectoralField
from participantes.jurados_forms import ResolucionJuradoForm, ReemplazoJuradoForm


class ResolucionJuradoMascaraTests(SimpleTestCase):
    def test_widget_resolucion_reutilizable(self):
        campo = ResolucionRectoralField()
        html = campo.widget.render("resolucion", "")
        self.assertIn('data-mask="resolucion"', html)
        self.assertIn('placeholder="3278/26-R"', html)
        self.assertIn('maxlength="9"', html)
        self.assertEqual(campo.clean("3278/26-R"), "3278/26-R")

    def test_formularios_jurados_usan_misma_mascara(self):
        # Los campos declarados se comparten entre los dos circuitos de resolución.
        for clase in (ResolucionJuradoForm, ReemplazoJuradoForm):
            with self.subTest(formulario=clase.__name__):
                campo = clase.base_fields["resolucion"]
                self.assertIsInstance(campo, ResolucionRectoralField)
                self.assertEqual(campo.widget.attrs["data-mask"], "resolucion")

    def test_rechaza_resoluciones_con_formato_ajeno_sin_javascript(self):
        campo = ResolucionRectoralField()
        for valor in ("327826", "12/26-R", "3278/26-r"):
            with self.subTest(valor=valor):
                with self.assertRaisesMessage(ValidationError, "Utilizá el formato 3278/26-R"):
                    campo.clean(valor)
        for valor in ("3278/26-CS", "3278/2026-R"):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    campo.clean(valor)
