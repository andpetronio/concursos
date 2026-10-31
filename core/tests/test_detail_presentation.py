"""Production detail presentation contracts for SDD-006 3A."""
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from concursos.services import crear_concurso
from concursos.tests.test_concursos import DATOS
from participantes.models import Aspirante, Jurado, Persona, Veedor


class DetailParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DetailPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="detail_qa", password="Synthetic-Only-2026!")
        cls.user.user_permissions.set(Permission.objects.all())
        cls.concurso = crear_concurso(datos=DATOS, usuario=cls.user)
        actor = {"creado_por": cls.user, "actualizado_por": cls.user}
        cls.people = [Persona.objects.create(nombre="Ana", apellido="Ejemplo", dni=f"9000000{i}", **actor)
                      for i in (1, 2)]
        cls.jurado = Jurado.objects.create(concurso=cls.concurso, persona=cls.people[0],
            representacion="rectorado", calidad="titular", titulo="Título de prueba",
            unidad="Unidad histórica", cargo="Cargo histórico", email="jurado@example.invalid",
            telefono="264 000 0000", **actor)
        cls.veedor = Veedor.objects.create(concurso=cls.concurso, persona=cls.people[1],
            cargo="Cargo veedor", email="veedor@example.invalid", telefono="264 000 0001", **actor)
        cls.aspirantes = [Aspirante.objects.create(concurso=cls.concurso, persona=person,
            email=f"aspirante{i}@example.invalid", expediente_inscripcion=f"01-{300+i}-2026", **actor)
            for i, person in enumerate(cls.people)]

    def setUp(self):
        self.client.post(reverse("login"), {"username": self.user.username, "password": "Synthetic-Only-2026!"})

    def detail(self, query=""):
        return self.client.get(self.concurso.get_absolute_url() + query)

    def test_cargo_is_heading_with_separate_administrative_and_documentary_facts(self):
        response = self.detail()
        self.assertContains(response, f'<h1 id="cargo-title">{self.concurso.denominacion}</h1>', html=True)
        for label in ("Expediente", "Modalidad", "Categoría", "Tramo", "Agrupamiento", "Estado administrativo", "Situación administrativa", "Etapa documental"):
            self.assertContains(response, label)
        self.assertContains(response, "El estado solo cambia con tu confirmación")
        self.assertContains(response, "los documentos verificados pueden sugerir un avance")
        for label, value in response.context["datos_concurso"]:
            if value is None or value == "":
                self.assertContains(response, "No registrado")
            else:
                self.assertContains(response, str(value))
        self.assertTemplateUsed(response, "expedientes/checklist.html")
        self.assertTemplateUsed(response, "documentos/seccion.html")

    def test_detail_groups_cover_all_fields_and_preserve_administrative_structure(self):
        from concursos.models import Concurso

        response = self.detail()
        grupos = response.context["grupos_datos_concurso"]
        codigos = [campo["codigo"] for grupo in grupos for campo in grupo["campos"]]
        self.assertCountEqual(codigos, (*Concurso.DATOS_EDITABLES, "tramo"))
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertContains(response, 'class="record-detail-groups"')
        self.assertContains(response, "Estructura administrativa")
        for codigo in ("unidad", "articulo_unidad", "dependencia", "articulo_dependencia",
                       "cadena_jerarquica", "articulo_superior"):
            self.assertIn(codigo, [campo["codigo"] for campo in grupos[1]["campos"]])

    def test_quick_missing_list_keeps_all_requisites_and_deep_links(self):
        response = self.detail()
        self.assertContains(response, 'data-document-quick-list')
        self.assertContains(response, 'data-document-quick-item=', count=21)
        self.assertContains(response, "Ver documentos faltantes")
        for seccion in response.context["secciones_documentales"]:
            for fila in seccion["filas"]:
                self.assertContains(response, f'href="#documental-{fila["control"].pk}"')
        self.assertContains(response, 'data-document-quick-stage')

    def test_edit_form_groups_articles_with_corresponding_administrative_units(self):
        response = self.client.get(reverse("concursos:editar", args=[self.concurso.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        ids = ("estructura-unidad-title", "estructura-dependencia-title", "estructura-superior-title")
        segmentos = [html.split(f'id="{identifier}"', 1)[1] for identifier in ids]
        segmentos = [segmentos[0].split(f'id="{ids[1]}"', 1)[0],
                    segmentos[1].split(f'id="{ids[2]}"', 1)[0], segmentos[2].split('class="form-grid structure-extras"', 1)[0]]
        for segmento, campos in zip(segmentos, (("unidad", "articulo_unidad"),
                                               ("dependencia", "articulo_dependencia"),
                                               ("cadena_jerarquica", "articulo_superior"))):
            for campo in campos:
                self.assertIn(f'name="{campo}"', segmento)

    def test_index_targets_unique_and_existing_fragment_ids_preserved(self):
        response = self.detail("?page=1&origen=prueba")
        self.assertContains(response, 'aria-label="Secciones de la ficha"')
        parser = DetailParser(response.content.decode())
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        for anchor in ("resumen", "datos-concurso", "jurados", "veedores", "aspirantes", "control-documental", "documentos", "historial"):
            self.assertIn(f"#{anchor}", parser.links)
            self.assertIn(anchor, parser.ids)
        for previous in ("estado-actual", "jurados-heading", "veedores-heading", "aspirantes-heading", "historial-title", "documental-heading", "documentos-heading"):
            self.assertIn(previous, parser.ids)
        self.assertContains(response, '#control-documental"')
        self.assertContains(response, 'id="control-')
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_people_homonyms_and_all_participation_data_remain_visible(self):
        response = self.detail()
        self.assertContains(response, '<strong>Ejemplo, Ana</strong>', count=4)
        self.assertTemplateUsed(response, "components/person_identity.html")
        for value in ("90000001", "90000002", "Título de prueba", "Unidad histórica", "Cargo registrado anteriormente: Cargo histórico", "Cargo veedor", "jurado@example.invalid", "veedor@example.invalid", "264 000 0000", "264 000 0001", "01-300-2026", "01-301-2026", "aspirante0@example.invalid", "aspirante1@example.invalid", "Rectorado", "Titular"):
            self.assertContains(response, value)
        self.assertContains(response, '<th scope="col">Unidad</th>', html=True)
        # Jurados y veedores conservan las acciones tradicionales; los aspirantes
        # usan el grupo compacto de tres íconos incorporado en SDD-006 F4C.
        self.assertContains(response, 'class="actions participation-actions"', count=1)
        self.assertContains(response, 'class="aspirant-actions" role="group"', count=3)
        self.assertContains(response, 'aria-label="Registrar presentación del jurado"', count=1)
        self.assertContains(response, "Desplazá la tabla horizontalmente", count=3)
        for kind, record in (("jurado", self.jurado), ("veedor", self.veedor), ("aspirante", self.aspirantes[0])):
            self.assertContains(response, reverse(f"concursos:{kind}_editar", args=[self.concurso.pk, record.pk]))
        self.assertContains(response, "Editar inscripción")
        self.assertContains(response, "Corregir persona")

    def test_reader_keeps_data_but_cannot_write(self):
        self.user.user_permissions.set(Permission.objects.filter(content_type__app_label="concursos", codename="view_concurso"))
        response = self.detail()
        self.assertContains(response, "90000001")
        for action in ("Editar participación", "Editar inscripción", "Corregir persona", "Agregar integrante", "Guardar etapa documental", "Editar datos"):
            self.assertNotContains(response, action)
        self.assertEqual(self.client.post(reverse("concursos:jurado_editar", args=[self.concurso.pk, self.jurado.pk]), {}).status_code, 403)

    def test_empty_detail_preserves_section_targets_and_messages(self):
        empty = crear_concurso(datos={**DATOS, "expediente": "01-2-2026"}, usuario=self.user)
        response = self.client.get(empty.get_absolute_url())
        for message in ("Todavía no hay integrantes", "No hay veedores registrados. El concurso puede continuar.", "Todavía no hay aspirantes", "Todavía no hay borradores generados."):
            self.assertContains(response, message)
        for anchor in ("jurados", "veedores", "aspirantes"):
            self.assertContains(response, f'id="{anchor}"')

    def test_other_pages_do_not_adopt_detail_composition(self):
        for url in (reverse("dashboard"), reverse("concursos:lista"), reverse("concursos:jurado_editar", args=[self.concurso.pk, self.jurado.pk])):
            response = self.client.get(url)
            self.assertNotContains(response, 'aria-label="Secciones de la ficha"')
            self.assertNotContains(response, 'class="actions participation-actions"')

    def test_progressive_tabs_preserve_all_panels_without_server_hiding(self):
        response = self.detail()
        self.assertContains(response, 'js/detail-tabs.js')
        self.assertContains(response, 'data-detail-panel', count=8)
        self.assertContains(response, 'data-detail-tab-navigation')
        self.assertNotContains(response, 'role="tab"')
        self.assertNotContains(response, 'data-detail-panel hidden')
        for anchor in ('resumen', 'datos-concurso', 'jurados', 'veedores', 'aspirantes',
                       'control-documental', 'documentos', 'historial'):
            self.assertContains(response, f'id="panel-{anchor}"')

    def test_direct_participant_posts_return_to_their_own_tabs(self):
        for kind, record in (("jurado", self.jurado), ("veedor", self.veedor), ("aspirante", self.aspirantes[0])):
            url = reverse(f"concursos:{kind}_editar", args=[self.concurso.pk, record.pk])
            form = self.client.get(url).context["form"]
            data = {field.name: field.value() or "" for field in form}
            data["email"] = f"{kind}.tabs@example.invalid"
            response = self.client.post(url, data)
            section = {"jurado": "jurados", "veedor": "veedores", "aspirante": "aspirantes"}[kind]
            self.assertRedirects(response, f"{self.concurso.get_absolute_url()}#{section}")
            record.refresh_from_db()
            self.assertEqual(record.email, data["email"])

    def test_person_correction_only_returns_to_known_linked_sections(self):
        url = reverse("concursos:persona_editar", args=[self.concurso.pk, self.people[0].pk])
        for section, expected in (("jurados", "jurados"), ("aspirantes", "aspirantes"),
                                  ("veedores", "resumen"), ("https://example.invalid/", "resumen"),
                                  ("", "resumen")):
            target = url + "?seccion=" + section
            form = self.client.get(target).context["form"]
            data = {field.name: field.value() or "" for field in form}
            response = self.client.post(target, data)
            self.assertRedirects(response, f"{self.concurso.get_absolute_url()}#{expected}")

    def test_invalid_control_keeps_errors_values_and_fragment_targets(self):
        control = self.concurso.controles_documentales.filter(requisito="propuesta_jurado_dependencia").first()
        if control is None:
            control = next(c for c in self.concurso.controles_documentales.all() if c.definicion.requiere_foja)
        prefix = f"control-{control.pk}"
        url = reverse("concursos:control_documental", args=[self.concurso.pk, control.pk])
        response = self.client.post(url, {f"{prefix}-version_esperada": control.version,
            f"{prefix}-fojas": "9/2", f"{prefix}-observaciones": "Texto ingresado conservado"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="field-errors"')
        self.assertContains(response, 'value="9/2"')
        self.assertContains(response, "Texto ingresado conservado")
        self.assertContains(response, f'id="documental-{control.pk}"')
        self.assertContains(response, 'id="panel-control-documental"')

    def test_history_pagination_preserves_query_and_tab_without_javascript(self):
        from concursos.models import CambioEstado
        CambioEstado.objects.bulk_create([
            CambioEstado(concurso=self.concurso, usuario=self.user,
                estado_anterior=self.concurso.estado, estado_nuevo=self.concurso.estado,
                situacion_anterior=self.concurso.situacion, situacion_nueva=self.concurso.situacion,
                justificacion="Historial de prueba") for _ in range(21)
        ])
        response = self.detail("?page=1&origen=prueba")
        links = DetailParser(response.content.decode()).links
        self.assertTrue(any("page=2" in link and "origen=prueba" in link and link.endswith("#historial")
                            for link in links))
