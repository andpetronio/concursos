from django.db import transaction
from django.utils import timezone
from django.utils.cache import patch_cache_control

from .models import SessionActivity
from .session_activity import expire_session, initialize_activity, intentional_navigation, is_expired


class InactivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        # Serializa lectura/renovación/operación entre pestañas de la misma sesión.
        # La fecha no vive en el JSON de sesión: una respuesta vieja no la pisa.
        with transaction.atomic():
            original_key = request.session.session_key
            activity = SessionActivity.objects.select_for_update().filter(
                session_id=original_key,
            ).first()
            now = timezone.now()
            if is_expired(activity, now):
                response = expire_session(request)
                patch_cache_control(response, private=True, no_store=True)
                return response
            request.session_activity = activity
            if (request.path == "/" or request.path.startswith(("/admin/", "/concursos/"))) and intentional_navigation(request):
                activity.last_activity = now
                activity.save(update_fields=["last_activity"])
            response = self.get_response(request)
            if request.user.is_authenticated and request.session.session_key != original_key:
                # cycle_key() nativo (cambio de contraseña) borra la sesión vieja.
                # Trasladar el reloj conserva el plazo, sin reiniciar actividad.
                initialize_activity(request, last_activity=activity.last_activity)
            patch_cache_control(response, private=True, no_store=True)
            return response
