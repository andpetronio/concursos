"""F4J.1: tablero de consulta con señales administrativas y documentales separadas.

El indicador de exigibilidad depende exclusivamente de la etapa *registrada*.
La etapa de atención solo orienta la navegación, sin escribir estados o etapas.
"""

from django.db.models import Count, Prefetch, Q
from django.urls import reverse

from concursos.choices import EstadoConcurso, SituacionAdministrativa
from concursos.models import Concurso
from concursos.services import sugerir_estado_convocado
from expedientes.catalogo import REQUISITOS, SECCIONES
from expedientes.models import ControlDocumental
from expedientes.services import detalle_sugerencia_estado
from participantes.models import Aspirante


MAX_PRIORIDADES = 8  # Por sección del tablero, no sobre la base de datos.
MAX_RECIENTES = 5


def construir_tablero(*, puede_cambiar_estado=False):
    """Una consulta agregada y relaciones precargadas; ninguna modificación.

    Las tres listas son excluyentes. Las tareas documentales habituales no
    se convierten en alertas administrativas ni en vencimientos supuestos.
    """
    totales = Concurso.objects.aggregate(
        total=Count("pk"),
        activos=Count("pk", filter=~Q(estado=EstadoConcurso.FINALIZADO)),
        con_dictamen=Count("pk", filter=Q(estado=EstadoConcurso.CON_DICTAMEN)),
        finalizados=Count("pk", filter=Q(estado=EstadoConcurso.FINALIZADO)),
    )
    concursos = list(
        Concurso.objects.exclude(estado=EstadoConcurso.FINALIZADO)
        .select_related("seguimiento_documental")
        .prefetch_related(
            Prefetch("controles_documentales", queryset=ControlDocumental.objects.only(
                "id", "concurso_id", "requisito", "verificado", "fojas", "version"
            )),
            Prefetch("aspirantes", queryset=Aspirante.objects.only("id", "concurso_id", "situacion")),
        )
        .order_by("-actualizado_en", "-pk")
    )
    etapas = [codigo for codigo, _ in SECCIONES]
    nombres_etapas = dict(SECCIONES)
    definiciones = {requisito.codigo: requisito for requisito in REQUISITOS}
    atencion = []
    documental = []
    sin_revision = []

    for concurso in concursos:
        controles = list(concurso.controles_documentales.all())
        por_codigo = {control.requisito: control for control in controles}
        etapa = concurso.seguimiento_documental.etapa
        indice_registrado = etapas.index(etapa)
        exigibles = set(etapas[:indice_registrado + 1])
        pendientes = [
            requisito for requisito in REQUISITOS
            if requisito.seccion in exigibles and (
                requisito.codigo not in por_codigo or not por_codigo[requisito.codigo].completo
            )
        ]
        # Mismo criterio visual que el Resumen individual: la última etapa
        # posterior con verificación, incluso si le falta la foja exigida.
        indice_atencion = indice_registrado
        for i, codigo in enumerate(etapas):
            if i > indice_registrado and any(
                c.verificado and definiciones[c.requisito].seccion == codigo
                for c in controles if c.requisito in definiciones
            ):
                indice_atencion = i
        etapa_atencion = etapas[indice_atencion]
        pendientes_en_foco = [
            requisito for requisito in REQUISITOS
            if requisito.seccion == etapa_atencion and (
                requisito.codigo not in por_codigo or not por_codigo[requisito.codigo].completo
            )
        ] if indice_atencion > indice_registrado else []
        # Una marca de verificación sin foja requiere completar datos:
        # priorizarla frente a controles aún no iniciados en esa misma etapa.
        pendientes_en_foco.sort(key=lambda r: (
            not (r.codigo in por_codigo and por_codigo[r.codigo].verificado),
        ))

        aspirantes = list(concurso.aspirantes.all())
        acta = por_codigo.get("acta_inscriptos")
        acta_sin_carga = bool(acta and acta.completo and not aspirantes)
        impugnaciones = sum(
            aspirante.situacion == Aspirante.Situacion.IMPUGNACION_PENDIENTE
            for aspirante in aspirantes
        )
        sugerencia = detalle_sugerencia_estado(concurso, controles)
        convocatoria = sugerir_estado_convocado(concurso)
        ficha = concurso.get_absolute_url()
        url_estado = reverse("concursos:estado", args=[concurso.pk])
        item = {
            "pk": concurso.pk,
            "expediente": concurso.expediente,
            "denominacion": concurso.denominacion,
            "estado": concurso.get_estado_display(),
            "situacion": concurso.get_situacion_display(),
            "etapa": nombres_etapas[etapa],
            "etapa_atencion": nombres_etapas[etapa_atencion],
            "atencion_diferente": indice_atencion > indice_registrado,
            "url": ficha,
            "actualizado_en": concurso.actualizado_en,
            "pendientes_exigibles": len(pendientes),
            "pendientes_foco": len(pendientes_en_foco),
            "completos": sum(c.completo for c in controles if c.requisito in definiciones),
            "total_controles": len(REQUISITOS),
            "aspirantes": len(aspirantes),
        }
        aviso_estado = None
        if sugerencia:
            aviso_estado = {
                "texto": f"Se sugiere revisar el estado «{sugerencia.nombre_estado}».",
                "url": url_estado + f"?sugerencia={sugerencia.requisito}"
                if puede_cambiar_estado else ficha + "#resumen",
            }
        elif convocatoria:
            aviso_estado = {
                "texto": "Hay convocatoria oficial registrada, pero el estado formal sigue en Preparación.",
                "url": url_estado + "?sugerencia=convocatoria"
                if puede_cambiar_estado else ficha + "#resumen",
            }
        item["aviso_estado"] = aviso_estado

        if concurso.situacion != SituacionAdministrativa.NORMAL:
            orden, motivo, detalle, destino = (
                0, "Revisar situación administrativa",
                f"Situación registrada: {concurso.get_situacion_display()}. No se presume su resolución.",
                ficha + "#resumen",
            )
            grupo = atencion
        elif acta_sin_carga:
            orden, motivo, detalle, destino = (
                1, "Conciliar el acta de inscriptos",
                "El acta está verificada, pero no hay aspirantes cargados. No se presume concurso desierto.",
                ficha + "#aspirantes",
            )
            grupo = atencion
        elif impugnaciones:
            orden, motivo, detalle, destino = (
                2, "Revisar impugnaciones de aspirantes",
                f"{impugnaciones} aspirante(s) con impugnación en trámite.",
                ficha + "#aspirantes",
            )
            grupo = atencion
        elif pendientes:
            primero = pendientes[0]
            control = por_codigo.get(primero.codigo)
            orden, motivo, detalle, destino = (
                0,
                "Completar referencia de fojas" if control and control.verificado else "Revisar control documental",
                primero.nombre,
                ficha + (f"#documental-{control.pk}" if control else "#control-documental"),
            )
            grupo = documental
        elif pendientes_en_foco:
            primero = pendientes_en_foco[0]
            control = por_codigo.get(primero.codigo)
            orden, motivo, detalle, destino = (
                1,
                "Completar referencia de fojas" if control and control.verificado else "Revisar actuaciones posteriores",
                f"{nombres_etapas[etapa_atencion]}: {primero.nombre}. "
                "Todavía no es exigible por la etapa registrada.",
                ficha + (f"#documental-{control.pk}" if control else "#control-documental"),
            )
            grupo = documental
        elif sugerencia:
            orden, motivo, detalle, destino = (
                3, "Revisar estado administrativo",
                f"El control «{sugerencia.nombre_documento}» permite sugerir «{sugerencia.nombre_estado}».",
                aviso_estado["url"],
            )
            grupo = atencion
        elif convocatoria:
            orden, motivo, detalle, destino = (
                4, "Revisar estado «Convocado»",
                f"Está registrada la Resolución N.º {concurso.resolucion_convocatoria}, "
                "pero el estado es Preparación.",
                aviso_estado["url"],
            )
            grupo = atencion
        else:
            sin_revision.append(item)
            continue

        item.update({"motivo": motivo, "detalle": detalle, "destino": destino, "orden": orden})
        grupo.append(item)

    # Orden estable: motivo, luego más recientemente actualizado (orden del queryset).
    atencion.sort(key=lambda item: item["orden"])
    documental.sort(key=lambda item: item["orden"])
    totales["atencion_administrativa"] = len(atencion)
    totales["seguimiento_documental"] = len(documental)
    totales["con_revision"] = len(atencion) + len(documental)
    return {
        "totales": totales,
        "atencion": atencion[:MAX_PRIORIDADES],
        "otras_atencion": max(0, len(atencion) - MAX_PRIORIDADES),
        "documental": documental[:MAX_PRIORIDADES],
        "otras_documental": max(0, len(documental) - MAX_PRIORIDADES),
        "sin_revision": sin_revision[:MAX_RECIENTES],
        "otras_sin_revision": max(0, len(sin_revision) - MAX_RECIENTES),
        "hay_concursos": bool(totales["total"]),
    }
