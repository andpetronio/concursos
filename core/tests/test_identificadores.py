from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.fields import IdentificadorField
from core.validators import normalizar_dni, validar_expediente


class IdentificadoresTests(SimpleTestCase):
    def test_dni_normalizado_preserva_ceros_y_separadores_anteriores(self):
        for valor in ("00123456", "00.123.456", "00-123-456", " 00 123 456 "):
            with self.subTest(valor=valor):
                self.assertEqual(normalizar_dni(valor), "00123456")
                self.assertEqual(IdentificadorField(formato="dni").clean(valor), "00123456")

    def test_dni_rechaza_longitud_incorrecta_letras_y_digitos_no_ascii(self):
        for valor in ("", "1234567", "123456789", "12a345678", "１２３４５６７８", "12/345/678", "..--"):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                normalizar_dni(valor)

    def test_expediente_central_variable_sin_relleno(self):
        for valor in ("01-1-2026", "01-758-2026", "01-2044-2026", "00-9999-0000"):
            with self.subTest(valor=valor):
                self.assertEqual(validar_expediente(valor), valor)

    def test_expediente_limites_y_separadores(self):
        for valor in ("1-1-2026", "001-1-2026", "01-0-2026", "01-0001-2026", "01-10000-2026",
                      "01--2026", "01-1-202", "01-1-20260", "01/1/2026", "01-a-2026", "01-1-2026\n"):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                validar_expediente(valor)

    def test_html_dni_con_y_sin_puntos_y_expediente_opcional(self):
        field = IdentificadorField(formato="dni")
        html = field.widget.render("dni", "00123456")
        self.assertIn('type="text"', html)
        self.assertIn('inputmode="numeric"', html)
        self.assertIn('value="00.123.456"', html)
        self.assertEqual(IdentificadorField(formato="expediente", required=False).clean(""), "")
