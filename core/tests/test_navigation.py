from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import get_script_prefix, resolve, reverse, set_script_prefix


class NavigationTests(SimpleTestCase):
    def render_navigation(self, view_name, kwargs=None, *, allowed=True):
        request = RequestFactory().get(reverse(view_name, kwargs=kwargs))
        request.resolver_match = resolve(request.path_info)
        return render_to_string("components/navigation.html", {
            "request": request,
            "perms": {
                "concursos": {"view_concurso": allowed},
                "documentos": {"configurar_institucion": allowed},
            },
        })

    def test_institutional_routes_share_one_active_section(self):
        for name in ("configuracion", "configuracion_personal", "membrete", "membrete_imagen"):
            with self.subTest(route=name):
                html = self.render_navigation(f"documentos:{name}")
                self.assertIn('href="' + reverse("documentos:configuracion") + '" aria-current="page"', html)
                self.assertEqual(html.count('aria-current="page"'), 1)

    def test_competitions_and_document_review_share_section(self):
        for name, kwargs in (("concursos:lista", None), ("documentos:revisar", {"pk": 1, "tipo": "convocatoria"})):
            with self.subTest(route=name):
                html = self.render_navigation(name, kwargs)
                self.assertIn('href="' + reverse("concursos:lista") + '" aria-current="page"', html)
                self.assertEqual(html.count('aria-current="page"'), 1)

    def test_institutional_section_under_deployment_prefix(self):
        prefix = get_script_prefix()
        try:
            set_script_prefix("/sicon/")
            request = RequestFactory().get(reverse("documentos:membrete"))
            request.resolver_match = resolve("/concursos/configuracion-institucional/membrete/")
            html = render_to_string("components/navigation.html", {
                "request": request,
                "perms": {"documentos": {"configurar_institucion": True}},
            })
            self.assertIn('href="/sicon/concursos/configuracion-institucional/" aria-current="page"', html)
        finally:
            set_script_prefix(prefix)

    def test_dashboard_is_the_only_active_section(self):
        html = self.render_navigation("dashboard")
        self.assertIn('href="/" aria-current="page"', html)
        self.assertEqual(html.count('aria-current="page"'), 1)

    def test_permissions_and_post_logout_are_preserved(self):
        html = self.render_navigation("dashboard", allowed=False)
        self.assertNotIn('href="' + reverse("concursos:lista") + '"', html)
        self.assertNotIn('href="' + reverse("documentos:configuracion") + '"', html)
        self.assertIn('action="' + reverse("logout") + '" method="post"', html)
        self.assertIn('type="submit"', html)

    def test_private_layout_has_progressive_mobile_controls(self):
        html = render_to_string("layouts/private.html", {
            "request": SimpleNamespace(user=SimpleNamespace(get_username=lambda: "prueba")),
        })
        self.assertIn('aria-controls="primary-navigation" aria-expanded="false"', html)
        self.assertIn('id="primary-navigation"', html)
        self.assertIn('js/navigation.js', html)
        self.assertNotIn('id="primary-navigation" hidden', html)

    def test_login_has_no_private_navigation_or_script(self):
        html = render_to_string("layouts/auth.html")
        self.assertNotIn('id="primary-navigation"', html)
        self.assertNotIn('js/navigation.js', html)
