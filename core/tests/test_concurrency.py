from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.test import Client, TransactionTestCase, skipUnlessDBFeature

from core.models import SessionActivity
from core.tests.test_auth import PASSWORD


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentSessionTests(TransactionTestCase):
    """La comprobación espera el reloj persistido, incluso entre requests solapados."""

    def test_waiting_request_observes_latest_activity(self):
        user = get_user_model().objects.create_user(username="operador_concurrente", password=PASSWORD)
        client = Client()
        client.post("/ingresar/", {"username": user.username, "password": PASSWORD})
        key = client.session.session_key
        selecting = Event()
        now = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        SessionActivity.objects.filter(session_id=key).update(last_activity=now - timedelta(seconds=1800))

        def observe_select(execute, sql, params, many, context):
            if "FOR UPDATE" in sql:
                selecting.set()
            return execute(sql, params, many, context)

        def read_from_another_tab():
            close_old_connections()
            try:
                tab = Client()
                tab.cookies = client.cookies.copy()
                with connection.execute_wrapper(observe_select):
                    return tab.get("/sesion/estado/").status_code
            finally:
                connection.close()

        with patch("django.utils.timezone.now", return_value=now):
            with ThreadPoolExecutor(max_workers=1) as pool:
                with transaction.atomic():
                    record = SessionActivity.objects.select_for_update().get(session_id=key)
                    future = pool.submit(read_from_another_tab)
                    self.assertTrue(selecting.wait(timeout=5))
                    self.assertFalse(future.done())
                    record.last_activity = now
                    record.save(update_fields=["last_activity"])
                self.assertEqual(future.result(timeout=10), 200)
