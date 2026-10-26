from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD
from participantes.forms import (AspiranteAltaForm, AspiranteEdicionForm, JuradoAltaForm,
                                 JuradoEdicionForm, PersonaEdicionForm, VeedorAltaForm, VeedorEdicionForm)
from participantes.models import Aspirante, Persona
from participantes.services import editar_persona


IDENTIDAD = {"apellido": "Prueba", "nombre": "Sintético", "dni": "00.123.456"}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AjustesAspirantesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="ajustes_ficticios", password=PASSWORD)
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.usuario)
        cls.otro = crear_concurso(datos=DATOS, usuario=cls.usuario)

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def url(self, name, concurso=None, *extra):
        return reverse(f"concursos:{name}", args=[(concurso or self.concurso).pk, *extra])

    def alta(self, concurso=None, **extra):
        return self.client.post(self.url("aspirante_crear", concurso), {**IDENTIDAD, **extra})

    def test_alta_consulta_edicion_y_contacto_independiente_por_inscripcion(self):
        self.assertEqual(self.alta(email="uno@example.invalid", expediente_inscripcion="01-758-2026").status_code, 302)
        self.assertEqual(self.alta(self.otro, email="otro@example.invalid", expediente_inscripcion="01-1-2026").status_code, 302)
        self.assertEqual(Persona.objects.count(), 1)
        persona = Persona.objects.get()
        self.assertEqual(persona.dni, "00123456")
        aspirante = Aspirante.objects.get(concurso=self.concurso)
        url = self.url("aspirante_editar", None, aspirante.pk)
        response = self.client.get(url)
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'value="01-758-2026"')
        self.assertEqual(self.client.post(url, {
            "email": "nuevo@example.invalid", "expediente_inscripcion": "01-2044-2026", "version_esperada": 1,
        }).status_code, 302)
        aspirante.refresh_from_db()
        self.assertEqual((aspirante.email, aspirante.expediente_inscripcion, aspirante.version),
                         ("nuevo@example.invalid", "01-2044-2026", 2))
        self.assertEqual(aspirante.actualizado_por, self.usuario)
        otro = Aspirante.objects.get(concurso=self.otro)
        self.assertEqual((otro.email, otro.expediente_inscripcion), ("otro@example.invalid", "01-1-2026"))
        detalle = self.client.get(self.concurso.get_absolute_url())
        self.assertContains(detalle, "nuevo@example.invalid")
        self.assertContains(detalle, "01-2044-2026")
        self.assertContains(detalle, url)
        persona.refresh_from_db()
        self.assertEqual(persona.version, 1)

    def test_campos_opcionales_y_vaciado_explicito(self):
        self.assertEqual(self.alta().status_code, 302)
        aspirante = Aspirante.objects.get()
        self.assertEqual((aspirante.email, aspirante.expediente_inscripcion), ("", ""))
        self.assertEqual(self.client.post(self.url("aspirante_editar", None, aspirante.pk), {
            "email": "", "expediente_inscripcion": "", "version_esperada": 1,
        }).status_code, 302)

    def test_email_y_expediente_invalidos_rechazados_en_alta_edicion_y_modelo(self):
        for campo, valor in (("email", "sin-arroba"), ("expediente_inscripcion", "01-0-2026")):
            with self.subTest(campo=campo):
                response = self.alta(**{campo: valor})
                self.assertIn(campo, response.context["form"].errors)
        self.assertEqual(Aspirante.objects.count(), 0)
        self.alta()
        aspirante = Aspirante.objects.get()
        for campo, valor in (("email", "sin-arroba"), ("expediente_inscripcion", "01-10000-2026")):
            response = self.client.post(self.url("aspirante_editar", None, aspirante.pk), {
                "email": "", "expediente_inscripcion": "", "version_esperada": 1, campo: valor,
            })
            self.assertIn(campo, response.context["form"].errors)
            setattr(aspirante, campo, valor)
            with self.assertRaises(ValidationError):
                aspirante.full_clean()
            setattr(aspirante, campo, "")
        aspirante.refresh_from_db()
        self.assertEqual(aspirante.version, 1)

    def test_repetir_expediente_no_relaja_unicidad_de_persona_en_concurso(self):
        self.alta(expediente_inscripcion="01-1-2026")
        response = self.alta(dni="00123456", expediente_inscripcion="01-1-2026")
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(self.alta(self.otro, expediente_inscripcion="01-1-2026").status_code, 302)
        self.assertEqual(self.alta(dni="00987654", expediente_inscripcion="01-1-2026").status_code, 302)
        self.assertEqual(Aspirante.objects.count(), 3)

    def test_version_obligatoria_y_formulario_viejo_no_sobrescriben_inscripcion(self):
        self.alta()
        aspirante = Aspirante.objects.get()
        url = self.url("aspirante_editar", None, aspirante.pk)
        datos = {"email": "primero@example.invalid", "expediente_inscripcion": "01-1-2026"}
        self.assertIn("version_esperada", self.client.post(url, datos).context["form"].errors)
        self.assertEqual(self.client.post(url, {**datos, "version_esperada": 1}).status_code, 302)
        response = self.client.post(url, {**datos, "email": "viejo@example.invalid", "version_esperada": 1})
        self.assertContains(response, "Otro operador modificó este registro")
        aspirante.refresh_from_db()
        self.assertEqual(aspirante.email, datos["email"])
        self.assertEqual(aspirante.version, 2)

    def test_edicion_anidada_y_permisos(self):
        self.alta()
        aspirante = Aspirante.objects.get()
        self.assertEqual(self.client.get(self.url("aspirante_editar", self.otro, aspirante.pk)).status_code, 404)
        self.usuario.user_permissions.remove(Permission.objects.get(codename="change_concurso"))
        url = self.url("aspirante_editar", None, aspirante.pk)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"version_esperada": 1}).status_code, 403)

    def test_dni_historico_no_se_reescribe_ni_bloquea_correccion_de_nombre(self):
        self.alta()
        persona = Persona.objects.get()
        Persona.objects.filter(pk=persona.pk).update(dni="1234567")  # Dato permitido antes del ajuste.
        persona.refresh_from_db()
        form = PersonaEdicionForm(instance=persona, data={
            "apellido": "Corregido", "nombre": persona.nombre, "dni": "1234567", "version_esperada": 1,
        })
        self.assertTrue(form.is_valid(), form.errors)
        response = self.client.post(self.url("persona_editar", None, persona.pk), form.data)
        self.assertEqual(response.status_code, 302)
        persona.refresh_from_db()
        self.assertEqual(persona.dni, "1234567")
        persona.dni = "123456789"
        with self.assertRaises(ValidationError):
            persona.save()

    def test_tipos_html_de_todos_los_formularios(self):
        for clase in (AspiranteAltaForm, JuradoAltaForm, VeedorAltaForm, PersonaEdicionForm):
            widget = clase().fields["dni"].widget
            self.assertEqual(widget.input_type, "text")
            self.assertEqual(widget.attrs["inputmode"], "numeric")
        for clase in (JuradoAltaForm, VeedorAltaForm, JuradoEdicionForm, VeedorEdicionForm):
            fields = clase().fields
            self.assertEqual(fields["telefono"].widget.input_type, "tel")
            self.assertEqual(fields["email"].widget.input_type, "email")
            attrs = fields["telefono"].widget.attrs
            self.assertEqual(attrs["data-mask"], "telefono")
            self.assertEqual(attrs["maxlength"], 11)
            self.assertEqual(attrs["placeholder"], "999-9999999")
            self.assertEqual(attrs["pattern"], r"[0-9]{3}-[0-9]{7}")
        self.assertEqual(AspiranteEdicionForm().fields["email"].widget.input_type, "email")

    def test_servicio_compara_dni_normalizado_antes_de_rechazar_cambio_compartido(self):
        self.alta()
        self.alta(self.otro)
        persona = Persona.objects.get()
        editar_persona(persona=persona, usuario=self.usuario, version_esperada=1,
                       datos={**IDENTIDAD, "apellido": "Corrección"})
        persona.refresh_from_db()
        self.assertEqual((persona.dni, persona.apellido, persona.version), ("00123456", "Corrección", 2))
