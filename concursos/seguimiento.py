"""Resumen orientativo, derivado de las fuentes existentes y sin escrituras.

Un control documental completo no acredita por sí mismo que un acto esté emitido
ni que el estado administrativo deba avanzar automáticamente.
"""


def panel_seguimiento(concurso, *, documentacion, secciones, cuadro, aspirantes):
    exigibles = set(documentacion.secciones_exigibles)
    etapas = []
    pendientes_exigibles = []
    pendientes_futuros = 0
    lista_futuros = []
    for seccion in secciones:
        codigo = seccion["codigo"]
        es_exigible = codigo in exigibles
        controles = []
        pendientes = []
        for fila in seccion["filas"]:
            control = fila["control"]
            requisito = fila["requisito"]
            item = {
                "id_control": control.pk,
                "nombre": requisito.nombre,
                "estado": fila["estado"],  # Misma clasificación que el checklist.
                "completo": control.completo,
                "fojas": control.fojas if requisito.requiere_foja else "",
                "foja_pendiente": control.verificado and not control.completo,
                "seccion": seccion["nombre"],
            }
            controles.append(item)
            if not control.completo:
                pendientes.append(item)
        # Una verificación sin foja aún requiere revisión, pero también
        # evidencia actividad documental en esa etapa.
        hay_actividad = any(fila["control"].verificado for fila in seccion["filas"])
        if codigo == documentacion.seguimiento.etapa:
            etiqueta = ("Etapa documental registrada · Controles completos" if not pendientes else
                        "Etapa documental registrada · Con controles pendientes")
        elif es_exigible:
            etiqueta = ("Etapa anterior · Controles completos" if not pendientes else
                        "Etapa anterior · Con controles pendientes")
        elif not pendientes:
            etiqueta = "Controles completos · Posterior a la etapa registrada"
        elif hay_actividad:
            etiqueta = "Actuaciones registradas · Controles futuros pendientes"
        else:
            etiqueta = "Etapa posterior · Aún no exigible"
        etapas.append({
            "codigo": codigo,
            "nombre": seccion["nombre"],
            "completos": seccion["completos"],
            "total": seccion["total"],
            "actual": codigo == documentacion.seguimiento.etapa,
            "futura": not es_exigible,
            "completa": not pendientes,
            "con_actividad": hay_actividad,
            "en_foco": False,
            "etiqueta": etiqueta,
            "controles": controles,
            "pendientes": len(pendientes),
        })
        if es_exigible:
            pendientes_exigibles.extend(pendientes)
        else:
            pendientes_futuros += len(pendientes)
            lista_futuros.extend(pendientes)

    # La etapa registrada es un dato formal: este foco solo decide qué
    # desplegable abrir al cargar el Resumen. Si hay actividad documentada
    # posterior, mostrar la más avanzada; si no, conservar la registrada.
    indice_registrado = next(
        (i for i, etapa in enumerate(etapas) if etapa["actual"]), 0
    )
    indice_atencion = indice_registrado
    for i, etapa in enumerate(etapas):
        if i > indice_registrado and etapa["con_actividad"]:
            indice_atencion = i
    etapas[indice_atencion]["en_foco"] = True
    atencion_diferente = indice_atencion != indice_registrado

    sin_continuidad = cuadro.get("sin_continuidad", [])
    evaluaciones_pendientes = cuadro.get("evaluaciones_pendientes", [])
    acta = next((c for c in documentacion.controles if c.requisito == "acta_inscriptos"), None)
    sin_carga = bool(acta and acta.completo and not aspirantes)
    avisos = []
    if concurso.situacion != "normal":
        avisos.append({
            "titulo": f"Situación administrativa: {concurso.get_situacion_display()}",
            "detalle": "Revisá la situación antes de continuar. El panel no levanta suspensiones ni resuelve impugnaciones.",
            "destino": "estado", "enlace": "Consultar estado y situación",
        })
    if sin_continuidad:
        avisos.append({
            "titulo": f"{len(sin_continuidad)} aspirante(s) sin continuidad vigente",
            "detalle": "No computan como evaluaciones pendientes ni integran el orden de mérito. Consultá sus actuaciones.",
            "destino": "aspirantes", "enlace": "Ver aspirantes",
        })
    if sin_carga:
        avisos.append({
            "titulo": "Acta de inscriptos verificada, sin aspirantes cargados",
            "detalle": "Conciliá la carga con el acta. La ausencia de registros no acredita por sí sola un concurso sin inscriptos.",
            "destino": "aspirantes", "enlace": "Revisar inscripciones",
        })
    if evaluaciones_pendientes and documentacion.seguimiento.etapa in ("oposicion", "finalizacion"):
        avisos.append({
            "titulo": f"{len(evaluaciones_pendientes)} evaluación(es) pendientes",
            "detalle": "Revisá los resultados cargados; el panel no asigna puntajes ni presupone inasistencias.",
            "destino": "aspirantes", "enlace": "Revisar evaluaciones",
        })

    # La sugerencia ya proviene del servicio de control documental. No se
    # deduce una transición nueva a partir de porcentajes o cantidad de checks.
    sugerencia = documentacion.detalle_sugerencia
    contraste = None
    if sugerencia:
        contraste = {
            "actual": concurso.get_estado_display(),
            "propuesto": sugerencia.nombre_estado,
            "documento": sugerencia.nombre_documento,
            "requisito": sugerencia.requisito,
        }

    # Una sola próxima revisión, priorizada por riesgos y datos verificables.
    # No supone vencimientos ni impone un orden obligatorio de actuaciones.
    if concurso.situacion != "normal":
        proxima = {
            "titulo": "Revisar la situación administrativa",
            "detalle": "El concurso tiene una situación especial registrada. Consultá las actuaciones antes de continuar.",
            "destino": "estado", "enlace": "Consultar situación",
        }
    elif sin_carga:
        proxima = {
            "titulo": "Conciliar el acta de inscriptos con la carga de aspirantes",
            "detalle": "El acta está verificada, pero SiCon no tiene aspirantes registrados. No presupone un concurso desierto.",
            "destino": "aspirantes", "enlace": "Revisar aspirantes",
        }
    elif pendientes_exigibles:
        primero = pendientes_exigibles[0]
        proxima = {
            "titulo": ("Completar las fojas del control" if primero["foja_pendiente"] else
                       "Revisar el próximo control documental"),
            "detalle": primero["nombre"],
            "destino": "control", "id_control": primero["id_control"],
            "enlace": "Ir al requisito",
        }
    elif sugerencia:
        proxima = {
            "titulo": "Revisar si corresponde actualizar el estado formal",
            "detalle": (f"El concurso figura en {concurso.get_estado_display()}; "
                       f"está verificado el control «{sugerencia.nombre_documento}». "
                       f"Si corresponde, un usuario autorizado puede confirmar {sugerencia.nombre_estado}."),
            "destino": "estado", "sugerencia": sugerencia.requisito,
            "enlace": "Revisar y confirmar",
        }
    elif sin_continuidad:
        proxima = {
            "titulo": "Revisar las situaciones individuales de aspirantes",
            "detalle": "Hay aspirantes sin continuidad vigente. Sus actuaciones se conservan en el historial.",
            "destino": "aspirantes", "enlace": "Ver aspirantes",
        }
    elif evaluaciones_pendientes and documentacion.seguimiento.etapa in ("oposicion", "finalizacion"):
        proxima = {
            "titulo": "Revisar evaluaciones pendientes",
            "detalle": "Hay evaluaciones sin registrar en la etapa documental seleccionada.",
            "destino": "aspirantes", "enlace": "Ver evaluaciones",
        }
    elif pendientes_futuros:
        proxima = {
            "titulo": "Revisar el avance de la etapa documental",
            "detalle": "No hay pendientes exigibles en la etapa registrada. Quedan controles de etapas futuras.",
            "destino": "documental", "enlace": "Consultar etapas y controles",
        }
    else:
        proxima = {
            "titulo": "Sin revisiones documentales pendientes detectadas",
            "detalle": "Los controles están completos. Esto no sustituye la revisión administrativa del expediente.",
            "destino": "documental", "enlace": "Consultar expediente",
        }

    return {
        "etapas": etapas,
        "completos": len(documentacion.completos),
        "total": documentacion.total,
        "pendientes_exigibles": pendientes_exigibles,
        "pendientes_futuros": pendientes_futuros,
        "primeros_futuros": lista_futuros[:3],
        "otros_futuros": max(0, len(lista_futuros) - 3),
        "primeros_pendientes": pendientes_exigibles[:4],
        "otros_pendientes": max(0, len(pendientes_exigibles) - 4),
        "avisos": avisos,
        "sugerencia_estado": sugerencia,
        "contraste_estado": contraste,
        "proxima_revision": proxima,
        "aspirantes_registrados": len(aspirantes),
        "sin_continuidad": len(sin_continuidad),
        "etapa_actual": documentacion.seguimiento.get_etapa_display(),
        "etapa_atencion": etapas[indice_atencion]["nombre"],
        "atencion_diferente": atencion_diferente,
    }
