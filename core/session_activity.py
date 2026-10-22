from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from .models import SessionActivity

IDLE_TIMEOUT = timedelta(seconds=1800)
ACTIVITY_INTERVAL = timedelta(seconds=30)


def initialize_activity(request, *, last_activity=None):
    # LoginView es el único ingreso, también para el administrador nativo.
    request.session.save()
    SessionActivity.objects.update_or_create(
        session_id=request.session.session_key,
        defaults={"last_activity": last_activity if last_activity is not None else timezone.now()},
    )


def is_expired(record, now):
    return record is None or now - record.last_activity >= IDLE_TIMEOUT


def expire_session(request):
    logout(request)
    if request.path in (reverse("session_activity"), reverse("session_status")):
        return JsonResponse({"expired": True}, status=401)
    return redirect(f"{reverse('login')}?expired=1")


def intentional_navigation(request):
    """Fetch Metadata diferencia navegación activada de recarga automática/prefetch.

    Es una señal funcional del navegador, no una prueba de presencia humana.
    """
    return (
        request.method == "GET"
        and request.headers.get("Sec-Fetch-Mode") == "navigate"
        and request.headers.get("Sec-Fetch-User") == "?1"
        and "prefetch" not in request.headers.get("Sec-Purpose", "").lower()
        and "prefetch" not in request.headers.get("Purpose", "").lower()
    )
