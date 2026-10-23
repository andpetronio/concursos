from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from concursos.catalogos import CATALOGO_CARGOS, categorias_para, opciones_dependientes, tramo_para
from concursos.choices import ModalidadConcurso
from concursos.forms import ConcursoForm
from concursos.models import Concurso
from concursos.services import crear_concurso, editar_concurso
from concursos.tests.test_concursos import DATOS, PASSWORD


class CatalogoTests(SimpleTestCase):
    def test_matriz_verificada_en_copla_y_sus_excepciones(self):
        esperado = {
            "01": {"Mayor": [1, 2, 3], "Intermedio": [4, 5], "Inicial": [6, 7]},
            "2A": {"Mayor": [1, 2, 3], "Intermedio": [4, 5]},
            "2B": {"Mayor": [2, 3], "Intermedio": [4, 5], "Inicial": [6, 7]},
            "03": {"Mayor": [2, 3], "Intermedio": [4, 5], "Inicial": [6, 7]},
            "4A": {"Mayor": [2, 3], "Intermedio": [4, 5], "Inicial": [6]},
            "4B": {"Mayor": [2, 3], "Intermedio": [4, 5], "Inicial": [6, 7]},
            "4C": {"Mayor": [1, 2, 3], "Intermedio": [4, 5], "Inicial": [6, 7]},
            "4D": {"Mayor": [3], "Intermedio": [4, 5], "Inicial": [6, 7]},
        }
        self.assertEqual({codigo: datos["tramos"] for codigo, datos in CATALOGO_CARGOS.items()}, esperado)
        for codigo, tramos in esperado.items():
            for tramo, numeros in tramos.items():
                for numero in numeros:
                    with self.subTest(codigo=codigo, numero=numero):
                        self.assertEqual(tramo_para(codigo, str(numero)), tramo)
                        self.assertIn(str(numero), categorias_para(codigo))
            invalidas = set(range(1, 8)) - {n for numeros in tramos.values() for n in numeros}
            for numero in invalidas:
                with self.subTest(codigo=codigo, invalida=numero), self.assertRaises(ValidationError):
                    tramo_para(codigo, str(numero))
        self.assertEqual(categorias_para("desconocido"), [])
        self.assertEqual(opciones_dependientes()["2A"][-1], {"categoria": "5", "tramo": "Intermedio"})


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ClasificacionConcursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="catalogo_ficticio", password=PASSWORD)
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos"))

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.usuario.username, "password": PASSWORD})

    def test_las_cuatro_modalidades_formulario_modelo_y_consulta(self):
        self.assertEqual(ModalidadConcurso.labels, ["Cerrado Interno", "Cerrado General", "Abierto", "Acotado"])
        for modalidad in ModalidadConcurso:
            with self.subTest(modalidad=modalidad):
                response = self.client.post(reverse("concursos:crear"), {**DATOS, "modalidad": modalidad})
                self.assertEqual(response.status_code, 302)
                concurso = Concurso.objects.get(modalidad=modalidad)
                self.assertEqual(concurso.get_modalidad_display(), modalidad.label)
                detalle = self.client.get(concurso.get_absolute_url())
                self.assertContains(detalle, modalidad.label)
                if modalidad == ModalidadConcurso.ACOTADO:
                    self.assertContains(detalle, "Ordenanza N.º 37/25-CS, Anexo, artículo 14")
                    self.assertEqual(concurso.situacion, "normal")
                    self.assertEqual(concurso.aspirantes.count(), 0)

    def test_rechazo_modalidades_invalidas_en_formulario_y_modelo(self):
        for modalidad in ("", "otro", "Cerrado Interno", "impugnado"):
            with self.subTest(modalidad=modalidad):
                form = ConcursoForm(data={**DATOS, "modalidad": modalidad})
                self.assertFalse(form.is_valid())
                self.assertIn("modalidad", form.errors)
                with self.assertRaises(ValidationError):
                    crear_concurso(datos={**DATOS, "modalidad": modalidad}, usuario=self.usuario)
        self.assertFalse(Concurso.objects.exists())

    def test_categorias_filtradas_en_post_y_edicion(self):
        form = ConcursoForm(data={**DATOS, "agrupamiento": "2A"})
        self.assertEqual([valor for valor, _ in form.fields["categoria"].choices], ["", "1", "2", "3", "4", "5"])
        self.assertTrue(form.is_valid(), form.errors)
        concurso = crear_concurso(datos={**DATOS, "agrupamiento": "2A"}, usuario=self.usuario)
        response = self.client.get(reverse("concursos:editar", args=[concurso.pk]))
        form = response.context["form"]
        self.assertEqual((form["agrupamiento"].value(), form["categoria"].value()), ("2A", "5"))
        self.assertEqual(form.tramo_calculado, "Intermedio")
        self.assertContains(response, 'value="2A" selected')
        self.assertContains(response, 'value="5" selected')
        self.assertNotContains(response, 'name="tramo"')
        self.assertContains(response, "Tramo calculado")

    def test_backend_rechaza_agrupamiento_categoria_y_tramo_inconsistentes(self):
        for cambios in ({"agrupamiento": "99"}, {"agrupamiento": "2A", "categoria": "7"},
                        {"agrupamiento": "4D", "categoria": "2"}, {"categoria": "8"}, {"tramo": "Mayor"}):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                crear_concurso(datos={**DATOS, **cambios}, usuario=self.usuario)
        for codigo, categoria in (("2A", "6"), ("4A", "7")):
            response = self.client.post(reverse("concursos:crear"), {**DATOS, "agrupamiento": codigo, "categoria": categoria})
            self.assertIn("categoria", response.context["form"].errors)
        self.assertFalse(Concurso.objects.exists())

    def test_tramo_se_deriva_sin_input_y_no_se_confia_en_post(self):
        datos = {**DATOS, "agrupamiento": "4D", "categoria": "3", "tramo": "Inicial"}
        response = self.client.post(reverse("concursos:crear"), datos)
        self.assertEqual(response.status_code, 302)
        concurso = Concurso.objects.get()
        self.assertEqual(concurso.tramo, "Mayor")
        concurso.tramo = "Inicial"
        with self.assertRaises(ValidationError):
            concurso.full_clean()

    def test_edicion_recalcula_tramo_y_conserva_datos_del_cargo_e_historial(self):
        concurso = crear_concurso(datos=DATOS, usuario=self.usuario)
        response = self.client.post(reverse("concursos:editar", args=[concurso.pk]), {
            **DATOS, "agrupamiento": "4D", "categoria": "3", "modalidad": "acotado", "version_esperada": 1,
        })
        self.assertEqual(response.status_code, 302)
        concurso.refresh_from_db()
        self.assertEqual((concurso.agrupamiento, concurso.categoria, concurso.tramo), ("4D", "3", "Mayor"))
        for campo in ("codigo_presupuestario", "denominacion", "funciones", "unidad", "dependencia", "cadena_jerarquica"):
            self.assertEqual(getattr(concurso, campo), DATOS[campo])
        self.assertEqual(concurso.historial.count(), 1)
        self.assertEqual(concurso.version, 2)
        with self.assertRaises(ValidationError):
            editar_concurso(pk=concurso.pk, datos=DATOS, usuario=self.usuario, version_esperada=1)

    def test_formulario_categorias_incorrectas_conserva_entrada_y_errores(self):
        response = self.client.post(reverse("concursos:crear"), {**DATOS, "agrupamiento": "2A", "categoria": "7", "modalidad": "acotado"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("categoria", response.context["form"].errors)
        self.assertContains(response, 'value="2A" selected')
        self.assertContains(response, 'value="acotado" selected')
        self.assertContains(response, DATOS["denominacion"])
        self.assertNotContains(response, 'id="referencia-acotado" class="notice" hidden')

    def test_alta_y_edicion_sin_javascript_permiten_elegir_categoria_y_guardar(self):
        for form in (ConcursoForm(), ConcursoForm(instance=Concurso(**DATOS)),
                     ConcursoForm(data={**DATOS, "agrupamiento": ""}),
                     ConcursoForm(data={**DATOS, "agrupamiento": "desconocido"})):
            self.assertEqual([valor for valor, _ in form.fields["categoria"].choices],
                             ["", "1", "2", "3", "4", "5", "6", "7"])
            self.assertFalse(form.fields["categoria"].widget.attrs.get("disabled", False))
        response = self.client.post(reverse("concursos:crear"), {k: v for k, v in DATOS.items() if k != "tramo"})
        self.assertEqual(response.status_code, 302)
        concurso = Concurso.objects.get()
        response = self.client.post(reverse("concursos:editar", args=[concurso.pk]), {
            **DATOS, "agrupamiento": "2A", "categoria": "3", "version_esperada": 1,
        })
        self.assertEqual(response.status_code, 302)
        concurso.refresh_from_db()
        self.assertEqual(concurso.tramo, "Mayor")
