from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from core.models import SessionActivity

START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
PASSWORD = "ClaveSoloParaPruebas-2026!"


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="operador_prueba", password=PASSWORD)

    def setUp(self):
        self.clock = patch("django.utils.timezone.now", return_value=START)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)

    def login(self, client=None):
        client = client or self.client
        return client.post(reverse("login"), {"username": self.user.username, "password": PASSWORD})

    def advance(self, seconds):
        self.now.return_value = START + timedelta(seconds=seconds)

    def activity_time(self):
        return SessionActivity.objects.get(session_id=self.client.session.session_key).last_activity

    def test_anonymous_is_denied(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, "/ingresar/?next=/", fetch_redirect_response=False)

    def test_valid_login_initializes_activity_and_rotates_session(self):
        session = self.client.session
        session["pre_login"] = True
        session.save()
        before = session.session_key
        self.assertRedirects(self.login(), "/", fetch_redirect_response=False)
        self.assertNotEqual(before, self.client.session.session_key)
        self.assertEqual(self.activity_time(), START)
        response = self.client.get("/")
        self.assertContains(response, "Panel inicial")
        self.assertIn("no-store", response.headers["Cache-Control"])
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_invalid_login_and_layout(self):
        response = self.client.post(reverse("login"), {"username": self.user.username, "password": "incorrecta"})
        self.assertContains(response, "El usuario o la contraseña no son correctos.")
        self.assertNotContains(response, 'class="sidebar"')
        self.assertEqual(SessionActivity.objects.count(), 0)

    def test_field_errors_have_accessible_association(self):
        response = self.client.post(reverse("login"), {})
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'aria-describedby="id_username_error"')
        self.assertContains(response, 'id="id_username_error"', count=1)

    def test_external_next_not_followed(self):
        response = self.client.post(reverse("login") + "?next=https://example.org/", {
            "username": self.user.username, "password": PASSWORD,
        })
        self.assertEqual(response.url, "/")

    def test_logout_get_does_not_destroy_session(self):
        self.login()
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_logout_post_invalidates_server_session(self):
        self.login()
        key = self.client.session.session_key
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"), fetch_redirect_response=False)
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.assertFalse(SessionActivity.objects.filter(session_id=key).exists())

    def test_csrf_login_logout_and_activity(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.login(client).status_code, 403)
        client.get(reverse("login"))
        token = client.cookies["csrftoken"].value
        response = client.post(reverse("login"), {
            "username": self.user.username, "password": PASSWORD, "csrfmiddlewaretoken": token,
        })
        self.assertEqual(response.status_code, 302)
        token = client.cookies["csrftoken"].value  # Rotado al autenticar.
        self.advance(100)
        self.assertEqual(client.post(reverse("session_activity")).status_code, 403)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        self.assertEqual(client.post(reverse("session_activity"), HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(client.post(reverse("logout"), HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_1799_seconds_allows_read_without_renewal(self):
        self.login()
        self.advance(1799)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.activity_time(), START)

    def test_exact_1800_and_later_expire(self):
        for seconds in (1800, 1801):
            with self.subTest(seconds=seconds):
                self.now.return_value = START
                self.login()
                key = self.client.session.session_key
                self.advance(seconds)
                response = self.client.get("/")
                self.assertEqual(response.url, "/ingresar/?expired=1")
                self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_valid_activity_at_1799_renews(self):
        self.login()
        self.advance(1799)
        self.assertEqual(self.client.post(reverse("session_activity")).status_code, 204)
        self.advance(1800)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.advance(3599)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_expired_activity_cannot_resurrect(self):
        self.login()
        self.advance(1800)
        self.assertEqual(self.client.post(reverse("session_activity")).status_code, 401)
        self.assertEqual(self.client.post(reverse("session_activity")).status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_expired_post_cannot_change_admin_data(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        self.login()
        self.advance(1800)
        count = get_user_model().objects.count()
        response = self.client.post(reverse("admin:auth_user_add"), {
            "username": "no_debe_crearse", "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertEqual(response.url, "/ingresar/?expired=1")
        self.assertEqual(get_user_model().objects.count(), count)

    def test_background_requests_never_renew(self):
        self.login()
        for seconds in (60, 600, 1799):
            self.advance(seconds)
            for path in ("/", "/health/", reverse("session_status"), "/static/css/app.css"):
                self.client.get(path)
            self.client.get("/", HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_PURPOSE="prefetch")
            self.assertEqual(self.activity_time(), START)
        self.advance(1800)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_health_and_status_do_not_count_even_with_navigation_headers(self):
        self.login()
        self.advance(100)
        for path in (reverse("health"), reverse("session_status")):
            self.client.get(path, HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1")
        self.assertEqual(self.activity_time(), START)

    def test_user_navigation_renews_but_prefetch_does_not(self):
        self.login()
        self.advance(100)
        self.client.get("/", HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1", HTTP_SEC_PURPOSE="prefetch")
        self.assertEqual(self.activity_time(), START)
        self.client.get("/", HTTP_SEC_FETCH_MODE="navigate", HTTP_SEC_FETCH_USER="?1")
        self.assertEqual(self.activity_time(), START + timedelta(seconds=100))

    def test_activity_rate_limit_and_methods(self):
        self.login()
        self.advance(29)
        self.assertEqual(self.client.post(reverse("session_activity")).status_code, 429)
        self.assertEqual(self.activity_time(), START)
        self.advance(30)
        self.assertEqual(self.client.post(reverse("session_activity")).status_code, 204)
        self.assertEqual(self.client.get(reverse("session_activity")).status_code, 405)

    def test_two_tabs_share_activity_and_expiry(self):
        self.login()
        tab = Client()
        tab.cookies = self.client.cookies.copy()
        self.advance(1700)
        self.assertEqual(tab.post(reverse("session_activity")).status_code, 204)
        self.advance(1800)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(tab.get(reverse("session_status")).json()["expires_in"], 1700)
        self.advance(3500)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(tab.get(reverse("session_status")).status_code, 401)

    def test_missing_activity_fails_closed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_admin_uses_common_login_and_respects_staff_permission(self):
        response = self.client.get(reverse("admin:login"))
        self.assertTrue(response.url.startswith("/ingresar/?next="))
        self.login()
        response = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(response.status_code, 403)
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_anonymous_admin_flow_returns_staff_to_index(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(response.resolver_match.url_name, "login")
        self.assertEqual(response.context["next"], reverse("admin:index"))
        response = self.client.post(reverse("login"), {
            "username": self.user.username, "password": PASSWORD, "next": response.context["next"],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.view_name, "admin:index")
        self.assertNotContains(response, "dark_mode.css")
        self.assertNotContains(response, "theme.js")
        self.assertContains(response, "js/session.js")

    def test_native_password_change_preserves_clock_across_rotation(self):
        self.user.is_staff = self.user.is_superuser = True
        self.user.save()
        self.login()
        original_key = self.client.session.session_key
        self.advance(100)
        new_password = "NuevaClaveParaPruebas-2026!"
        response = self.client.post(reverse("admin:password_change"), {
            "old_password": PASSWORD, "new_password1": new_password, "new_password2": new_password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.view_name, "admin:password_change_done")
        self.assertNotEqual(original_key, self.client.session.session_key)
        self.assertEqual(self.activity_time(), START)
        self.assertFalse(Session.objects.filter(session_key=original_key).exists())
        self.advance(1800)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_activity_crossing_timeout_between_middleware_and_view_is_rejected(self):
        self.login()
        key = self.client.session.session_key
        middleware_clock = SimpleNamespace(now=lambda: START + timedelta(seconds=1799))
        view_clock = SimpleNamespace(now=lambda: START + timedelta(seconds=1800))
        with patch("core.middleware.timezone", middleware_clock), patch("core.views.timezone", view_clock):
            self.assertEqual(self.client.post(reverse("session_activity")).status_code, 401)
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_status_anonymous_and_expired(self):
        self.assertEqual(self.client.get(reverse("session_status")).status_code, 401)
        self.login()
        self.advance(1800)
        self.assertEqual(self.client.get(reverse("session_status")).status_code, 401)
