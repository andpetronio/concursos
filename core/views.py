from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.shortcuts import render

from .forms import LoginForm
from .session_activity import (
    ACTIVITY_INTERVAL, IDLE_TIMEOUT, expire_session, initialize_activity, is_expired,
)


class LoginView(DjangoLoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        initialize_activity(self.request)
        return response


@login_required
def dashboard(request):
    contexto = {}
    if request.user.has_perm("concursos.view_concurso"):
        from .tablero import construir_tablero
        contexto["tablero"] = construir_tablero(
            puede_cambiar_estado=request.user.has_perm("concursos.cambiar_estado_concurso"),
        )
    return render(request, "core/dashboard.html", contexto)


@never_cache
@require_POST
@csrf_protect
def activity(request):
    if not request.user.is_authenticated:
        return JsonResponse({"expired": True}, status=401)
    # El middleware ya tomó el lock y rechazó sesiones vencidas.
    now = timezone.now()
    record = request.session_activity
    if is_expired(record, now):
        return expire_session(request)
    if now - record.last_activity < ACTIVITY_INTERVAL:
        return JsonResponse({"retry_after": 30}, status=429, headers={"Retry-After": "30"})
    record.last_activity = now
    record.save(update_fields=["last_activity"])
    return HttpResponse(status=204)


@never_cache
def session_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({"expired": True}, status=401)
    now = timezone.now()
    if is_expired(request.session_activity, now):
        return expire_session(request)
    remaining = IDLE_TIMEOUT - (now - request.session_activity.last_activity)
    return JsonResponse({"expires_in": max(0, remaining.total_seconds())})


def health(request):
    return HttpResponse("ok", content_type="text/plain")
