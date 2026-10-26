from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.fields import IdentificadorField, TelefonoField
from core.validators import normalizar_dni, validar_expediente, normalizar_telefono, validar_codigo_presupuestario


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

    def test_mascaras_limites_y_sin_boton_agregar_guion(self):
        dni = IdentificadorField(formato="dni", max_length=20)
        expediente = IdentificadorField(formato="expediente", max_length=100)
        telefono = TelefonoField()
        self.assertIn('maxlength="10"', dni.widget.render("dni", "00123456"))
        self.assertIn('maxlength="12"', expediente.widget.render("expediente", "01-1-2026"))
        self.assertIn('maxlength="11"', telefono.widget.render("telefono", "264-1234567"))
        self.assertIn('data-mask="telefono"', telefono.widget.render("telefono", ""))
        self.assertNotIn("Agregar guion", expediente.widget.render("expediente", "01-1-2026"))
        self.assertNotIn("Agregar guion", expediente.help_text)
        self.assertEqual(expediente.clean("01-9999-2026"), "01-9999-2026")

    def test_telefono_nuevo_y_codigo_presupuestario_validan_en_servidor(self):
        self.assertEqual(normalizar_telefono("2641234567"), "264-1234567")
        self.assertEqual(normalizar_telefono("264-1234567"), "264-1234567")
        self.assertEqual(TelefonoField().clean(""), "")
        for invalido in ("2", "123-4567", "264-12345678", "26a-1234567", "00123456789"):
            with self.subTest(invalido=invalido), self.assertRaises(ValidationError):
                TelefonoField().clean(invalido)
        self.assertEqual(validar_codigo_presupuestario("10972"), "10972")
        self.assertEqual(validar_codigo_presupuestario("A-12"), "A-12")
        with self.assertRaises(ValidationError):
            validar_codigo_presupuestario("123456")

    def test_telefono_historico_se_conserva_sin_aceptar_otro_invalido(self):
        telefono = TelefonoField()
        telefono.conservar_actual("2")
        self.assertEqual(telefono.clean("2"), "2")
        with self.assertRaises(ValidationError):
            telefono.clean("3")
        self.assertEqual(telefono.clean("2641234567"), "264-1234567")
