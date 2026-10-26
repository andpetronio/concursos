from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def navigation_section(context):
    """Clasifica la sección sin acoplarla a nombres de vistas institucionales."""
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if not match:
        return ""
    if match.namespace == "documentos":
        if request.path.startswith(reverse("documentos:configuracion")):
            return "configuracion"
        return "concursos"
    if match.namespace == "concursos":
        return "concursos"
    return "dashboard" if match.view_name == "dashboard" else ""
