import hashlib
from datetime import date
import json
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from django.conf import settings
from participantes.models import Jurado, Aspirante, Persona
from participantes.evaluaciones import cuadro_resultados, faltantes_resultados
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from concursos.models import Concurso
from expedientes import services as expediente_services
from .models import DestinatarioAPUNSJ, DestinatarioPersonal, GeneracionDocumento, MembreteInstitucional
from .registry import TIPOS, POR_CODIGO, nombre_miembro
from .renderers import renderizar

PERMISOS_GENERACION = ("concursos.view_concurso", "documentos.generar_documento")


def faltantes_generales(concurso):
    # La validación existente respeta datos históricos sin imponer una migración de ellos.
    faltantes = []
    try:
        concurso.full_clean()
    except ValidationError:
        faltantes.append("Revisar los datos generales del concurso.")
    for campo in Concurso.DATOS_EDITABLES:
        definicion = concurso._meta.get_field(campo)
        if not definicion.blank and not str(getattr(concurso, campo)).strip():
            faltantes.append(f"Completar {definicion.verbose_name} del concurso.")
    return faltantes


def faltantes_convocatoria(concurso, controles=None):
    faltantes = []
    if not concurso.turno_trabajo:
        faltantes.append("Seleccionar turno de trabajo (mañana o tarde) en Datos del concurso.")
    if not concurso.domicilio_trabajo:
        faltantes.append("Completar domicilio de trabajo en Datos del concurso.")
    if not concurso.jurisdiccion:
        faltantes.append("Seleccionar jurisdicción en Datos del concurso.")
    if not concurso.iniciador_nombre or not concurso.iniciador_cargo:
        faltantes.append("Completar nombre y cargo del iniciador del expediente.")
    if not concurso.causa_vacancia:
        faltantes.append("Seleccionar la causa de vacancia del cargo.")
    if concurso.causa_vacancia in {"jubilacion", "renuncia", "fallecimiento", "concurso", "efectivizacion"} and not concurso.ex_titular:
        faltantes.append("Completar ex titular para la causa de vacancia seleccionada.")
    if concurso.causa_vacancia in {"jubilacion", "renuncia", "concurso", "efectivizacion"} and not (concurso.resolucion_baja or concurso.acto_vacancia):
        faltantes.append("Completar resolución o acto acreditado de la vacancia.")
    if concurso.causa_vacancia == "traslado" and not concurso.acto_vacancia:
        faltantes.append("Completar el acto administrativo que acredita el traslado del cargo.")
    if concurso.causa_vacancia == "otra" and not concurso.detalle_vacancia:
        faltantes.append("Completar descripción acreditada para Otra causa de vacancia.")
    if controles is None:
        afectacion = concurso.controles_documentales.filter(requisito="afectacion_presupuestaria").first()
    else:
        afectacion = next((c for c in controles if c.requisito == "afectacion_presupuestaria"), None)
    if not afectacion or not afectacion.partida_principal:
        faltantes.append("Completar código de unidad principal (PPAL) en la afectación presupuestaria.")
    if not afectacion or not afectacion.actividad_presupuestaria:
        faltantes.append("Completar código de actividad en la afectación presupuestaria.")
    return faltantes


def faltantes_jurisdiccion_oficios(concurso, tipo):
    """Los oficios previos necesitan la jurisdicción, aun sin resolución de convocatoria."""
    if tipo.codigo == "elecciones" and not concurso.jurisdiccion:
        return ["Seleccionar jurisdicción en Datos del concurso antes de generar el oficio."]
    return []


def faltantes_destinatario(destinatario):
    if destinatario is None:
        return ["Configurar tratamiento, cargo, nombre y apellido del destinatario de APUNSJ."]
    try:
        destinatario.full_clean()
    except ValidationError as error:
        return [f"Destinatario APUNSJ: {mensaje}" for mensaje in error.messages]
    return []


def faltantes_desierto_inscriptos(concurso, *, instantanea=None):
    """Actuación formal independiente del dictamen; fuente auténtica: acta verificada."""
    if instantanea is None:
        control = concurso.controles_documentales.filter(requisito="acta_inscriptos").first()
        acta_ok = bool(control and control.completo)
        sin_aspirantes = not concurso.aspirantes.exists()
    else:
        acta_ok = any(a["requisito"] == "acta_inscriptos" and a["fojas"]
                      for a in instantanea["actuaciones_verificadas"])
        sin_aspirantes = not instantanea["aspirantes"]
    faltantes = []
    if not acta_ok:
        faltantes.append("Verificar el acta de cierre de inscripciones e indicar sus fojas en Control documental.")
    if not sin_aspirantes:
        faltantes.append("Hay aspirantes registrados: este modelo corresponde exclusivamente a concursos sin inscriptos.")
    if not concurso.resolucion_convocatoria:
        faltantes.append("Registrar la resolución oficial de convocatoria en Datos del concurso.")
    # La parte dispositiva usa la jurisdicción; bloquear antes de renderizar
    # evita un KeyError y, sobre todo, evita inventar un destino institucional.
    if not concurso.jurisdiccion:
        faltantes.append("Seleccionar jurisdicción en Datos del concurso antes de generar la resolución.")
    if concurso.modalidad not in ("cerrado_interno", "cerrado_general"):
        faltantes.append("No se definió un nuevo llamado automático para esta modalidad; requiere revisión específica.")
    return faltantes


def disponibilidad(concurso, tipo, destinatario=None):
    faltantes = []
    if tipo.fuente and not fuente_original(tipo).is_file():
        faltantes.append(f"Modelo original no disponible: {tipo.fuente}.")
    if tipo.codigo == "convocatoria":
        # Habilitación central obligatoria; la presencia del modelo no la sustituye.
        faltantes.extend(expediente_services.habilitacion_convocatoria(concurso).faltantes)
        faltantes.extend(faltantes_convocatoria(concurso))
    if tipo.codigo != "convocatoria":
        faltantes.extend(faltantes_generales(concurso))
    faltantes.extend(faltantes_jurisdiccion_oficios(concurso, tipo))
    if tipo.codigo in ("jurados", "dictamen", "designacion"):
        faltantes.extend(expediente_services.habilitacion_convocatoria(concurso).pendientes_jurado)
    faltantes.extend(faltantes_antecedentes(concurso, tipo))
    if tipo.codigo == "dictamen":
        faltantes.extend(faltantes_resultados(cuadro_resultados(concurso)))
    if tipo.codigo == "desierto_inscriptos":
        faltantes.extend(faltantes_desierto_inscriptos(concurso))
    if tipo.codigo == "apunsj":
        faltantes.extend(faltantes_destinatario(destinatario))
        if not concurso.resolucion_convocatoria:
            faltantes.append("Registrar la resolución oficial de convocatoria en Datos del concurso antes de solicitar el veedor.")
    if tipo.codigo == "elecciones":
        if concurso.modalidad != "cerrado_interno":
            faltantes.append("El modelo de elección del personal corresponde a Concurso Cerrado Interno; se requiere modelo específico para esta modalidad.")
        if not DestinatarioPersonal.objects.filter(pk=1).exists():
            faltantes.append("Configurar la jefatura del Departamento de Personal antes de generar el oficio.")
        if not concurso.causa_vacancia or (concurso.causa_vacancia != "nuevo" and not concurso.fecha_baja):
            faltantes.append("Completar causa y fecha de vacancia en Datos del concurso.")
        if concurso.causa_vacancia == "traslado" and not concurso.acto_vacancia:
            faltantes.append("Completar el acto administrativo que acredita el traslado del cargo.")
        if concurso.causa_vacancia == "otra" and not concurso.detalle_vacancia:
            faltantes.append("Completar el antecedente acreditado de vacancia (otra causa).")
        if concurso.causa_vacancia in ("concurso", "efectivizacion", "jubilacion", "renuncia", "fallecimiento") and not concurso.ex_titular:
            faltantes.append("Completar el ex titular del cargo para fundamentar la vacancia.")
    if tipo.codigo in ("elecciones", "apunsj") and not MembreteInstitucional.objects.filter(pk=1).exists():
        faltantes.append("Cargar el membrete vigente en Configuración institucional antes de generar el oficio.")
    if tipo.codigo == "jurados" and not concurso.resolucion_convocatoria:
        faltantes.append("Registrar la resolución oficial de convocatoria en Datos del concurso antes de notificar a los jurados.")
    if tipo.codigo == "jurados" and not MembreteInstitucional.objects.filter(pk=1).exists():
        faltantes.append("Cargar el membrete vigente en Configuración institucional antes de generar las notificaciones.")
    return {"tipo": tipo, "faltantes": faltantes, "disponible": not faltantes}


REQUISITOS_POSTERIORES = ("acta_inscriptos", "valoracion_antecedentes", "sorteo_temas", "acta_oposicion", "dictamen", "comunicacion_dictamen")


def faltantes_antecedentes(concurso, tipo, controles=None, aspirantes=None):
    faltantes = []
    if tipo.codigo in ("dictamen", "designacion"):
        from expedientes.catalogo import POR_CODIGO as REQUISITOS
        controles = list(concurso.controles_documentales.all()) if controles is None else controles
        completos = {c.requisito for c in expediente_services.consultar_documentacion(concurso, controles=controles).completos}
        requeridos = REQUISITOS_POSTERIORES + (("aprobacion_dictamen", "afectacion_presupuestaria") if tipo.codigo == "designacion" else ())
        faltantes.extend(f"Completar actuación y foja correspondiente: {REQUISITOS[codigo].nombre}."
                         for codigo in requeridos if codigo not in completos)
        if not (concurso.aspirantes.exists() if aspirantes is None else aspirantes):
            faltantes.append("Registrar los aspirantes del acta de inscriptos.")
    return faltantes


# Agrupación exclusivamente de presentación: no cambia el catálogo ni la habilitación.
GRUPOS_PRESENTACION = (
    ("preparatorios", "Oficios preparatorios", "Solicitudes anteriores a la resolución de convocatoria.",
     ("elecciones",)),
    ("convocatoria", "Convocatoria y comunicaciones", "Proyecto de convocatoria y comunicaciones vinculadas.",
     ("convocatoria", "jurados", "apunsj")),
    ("posteriores", "Actuaciones posteriores", "Proyectos sujetos a antecedentes y validación administrativa.",
     ("dictamen", "designacion", "desierto_inscriptos")),
)


def contexto_documentos(concurso, *, usuario=None, formulario_error_tipo=None, formulario_error=None):
    destinatario = DestinatarioAPUNSJ.objects.filter(pk=1).first()
    documentos = [disponibilidad(concurso, tipo, destinatario) for tipo in TIPOS]
    por_codigo = {documento["tipo"].codigo: documento for documento in documentos}
    grupos = [{"codigo": codigo, "titulo": titulo, "descripcion": descripcion,
               "documentos": [por_codigo[tipo] for tipo in codigos],
               "listos": sum(por_codigo[tipo]["disponible"] for tipo in codigos)}
              for codigo, titulo, descripcion, codigos in GRUPOS_PRESENTACION]
    if usuario is not None and usuario.has_perms(PERMISOS_GENERACION):
        # Un solo preparador de formularios sirve tanto para la ficha completa
        # como para el fragmento de disponibilidad consultado en vivo.
        from .forms import GeneracionForm
        for documento in documentos:
            tipo = documento["tipo"]
            if not documento["disponible"] and tipo.codigo != formulario_error_tipo:
                continue
            snapshot, _, _, destinatario_actual = fuentes_actuales(concurso, tipo)
            inicial = {
                "huella_esperada": huella_fuentes(snapshot),
                "version_concurso": concurso.version,
                "version_destinatario": destinatario_actual.version if destinatario_actual else 0,
            }
            formulario = formulario_error if tipo.codigo == formulario_error_tipo else None
            if formulario is None:
                formulario = GeneracionForm(
                    initial=inicial, prefix=tipo.codigo, tipo=tipo, concurso=concurso,
                    acotado=concurso.modalidad == "acotado" and tipo.codigo != "apunsj",
                )
            campos = list(formulario.visible_fields())
            documento["formulario"] = formulario
            documento["campos_complementarios"] = [c for c in campos
                if c.name != "revision_administrativa" and not c.name.startswith("presupuesto_")]
            documento["campos_presupuesto"] = [c for c in campos if c.name.startswith("presupuesto_")]
            documento["campo_revision"] = next((c for c in campos if c.name == "revision_administrativa"), None)
            documento["tiene_complementos"] = bool(campos)
            documento["formulario_con_errores"] = bool(formulario.errors)
    return {"tipos_documentos": documentos, "grupos_tipos_documentos": grupos,
            "documentos_listos": sum(documento["disponible"] for documento in documentos),
            "generaciones": concurso.documentos_generados.select_related("generado_por")[:20]}


@transaction.atomic
def guardar_destinatario(*, datos, usuario, version_esperada):
    if not usuario.has_perm("documentos.configurar_institucion"):
        raise PermissionDenied
    destinatario = DestinatarioAPUNSJ.objects.select_for_update().filter(pk=1).first()
    version = destinatario.version if destinatario else 0
    if version != version_esperada:
        raise ValidationError("Otro operador modificó el destinatario. Volvé a abrir la configuración antes de guardar.")
    nuevo = destinatario is None
    if nuevo:
        destinatario = DestinatarioAPUNSJ(pk=1, creado_por=usuario)
    for campo in ("tratamiento", "cargo", "titulo", "nombre", "apellido"):
        setattr(destinatario, campo, datos[campo].strip())
    destinatario.actualizado_por = usuario
    destinatario.version = version + 1
    destinatario.full_clean()
    try:
        with transaction.atomic():
            destinatario.save(force_insert=nuevo)
    except IntegrityError:
        raise ValidationError("Otro operador configuró el destinatario. Volvé a abrir la configuración.")
    return destinatario


@transaction.atomic
def guardar_destinatario_personal(*, datos, usuario, version_esperada):
    if not usuario.has_perm("documentos.configurar_institucion"):
        raise PermissionDenied
    actual = DestinatarioPersonal.objects.select_for_update().filter(pk=1).first()
    if (actual.version if actual else 0) != version_esperada:
        raise ValidationError("La jefatura de Personal cambió. Volvé a abrir la configuración.")
    nuevo = actual is None
    if nuevo:
        actual = DestinatarioPersonal(pk=1)
    for campo in ("tratamiento", "cargo", "titulo", "nombre", "apellido"):
        setattr(actual, campo, datos[campo].strip())
    actual.actualizado_por = usuario
    actual.version = version_esperada + 1
    actual.full_clean()
    try:
        with transaction.atomic():
            actual.save(force_insert=nuevo)
    except IntegrityError as error:
        raise ValidationError("Otro operador modificó la jefatura de Personal.") from error
    return actual



@transaction.atomic
def guardar_membrete(*, imagen, usuario, version_esperada):
    """Reemplazo controlado: un único membrete, sin modificar documentos históricos."""
    if not usuario.has_perm("documentos.configurar_institucion"):
        raise PermissionDenied
    # La validación también reside en el servicio: ningún llamador puede saltear el formulario.
    from docx.image.image import Image as ImagenDocx
    blob = imagen.get("contenido")
    if not isinstance(blob, bytes) or len(blob) > 4 * 1024 * 1024 or len(blob) == 0:
        raise ValidationError("El membrete debe ser una imagen válida de hasta 4 MB.")
    try:
        info = ImagenDocx.from_blob(blob)
    except Exception as error:
        raise ValidationError("El membrete debe ser un PNG o JPG válido.") from error
    if (info.content_type not in ("image/png", "image/jpeg") or
            imagen.get("tipo_mime") != info.content_type or
            info.px_width < 300 or info.px_height < 60 or
            info.px_width * info.px_height > 16_000_000):
        raise ValidationError("Formato o dimensiones del membrete no admitidos.")
    actual = MembreteInstitucional.objects.select_for_update().filter(pk=1).first()
    version = actual.version if actual else 0
    if version != version_esperada:
        raise ValidationError("El membrete cambió. Volvé a abrir la configuración antes de guardar.")
    nuevo = actual is None
    if nuevo:
        actual = MembreteInstitucional(pk=1)
    actual.contenido = imagen["contenido"]
    actual.tipo_mime = imagen["tipo_mime"]
    actual.nombre_archivo = imagen["nombre_archivo"]
    actual.sha256 = hashlib.sha256(imagen["contenido"]).hexdigest()
    actual.version = version + 1
    actual.actualizado_por = usuario
    try:
        with transaction.atomic():
            actual.save(force_insert=nuevo)
    except IntegrityError as error:
        raise ValidationError("Otro operador actualizó el membrete. Volvé a abrir la configuración.") from error
    return actual

def instantanea_concurso(concurso):
    campos = (*Concurso.DATOS_EDITABLES, "tramo")
    def seguro(valor):
        return valor.isoformat() if isinstance(valor, date) else valor
    datos = {campo: seguro(getattr(concurso, campo)) for campo in campos}
    datos.update(id=concurso.pk, version=concurso.version)
    datos["datos_presentados"] = [
        [concurso._meta.get_field(campo).verbose_name.capitalize(),
         str(seguro(getattr(concurso, f"get_{campo}_display", lambda: getattr(concurso, campo))()) or "")]
        for campo in campos
    ]
    return datos


def fuente_original(tipo):
    return Path(settings.BASE_DIR) / "documentos" / "modelos" / tipo.fuente


def _participantes(concurso, modelo, bloquear):
    consulta = modelo.objects.filter(concurso=concurso).order_by("pk")
    registros = list(consulta.select_for_update() if bloquear else consulta)
    personas = Persona.objects.filter(pk__in=[r.persona_id for r in registros]).order_by("pk")
    personas = {p.pk: p for p in (personas.select_for_update() if bloquear else personas)}
    for registro in registros:
        registro.persona = personas[registro.persona_id]
    return registros


def fuentes_actuales(concurso, tipo, *, bloquear=False):
    controles = concurso.controles_documentales.order_by("pk")
    controles = list(controles.select_for_update() if bloquear else controles)
    jurados = _participantes(concurso, Jurado, bloquear) if tipo.codigo in ("convocatoria", "jurados", "dictamen", "designacion") else []
    aspirantes = _participantes(concurso, Aspirante, bloquear) if tipo.codigo in ("dictamen", "designacion", "desierto_inscriptos") else []
    def persona(registro):
        return {campo: getattr(registro.persona, campo) for campo in ("id", "nombre", "apellido", "dni", "version")}
    def participacion(registro, campos):
        return {"id": registro.pk, "persona": persona(registro),
                **{campo: getattr(registro, campo) for campo in campos}}
    destinatario = None
    if tipo.codigo == "apunsj":
        consulta = DestinatarioAPUNSJ.objects.filter(pk=1)
        destinatario = (consulta.select_for_update() if bloquear else consulta).first()
    jefatura = None
    if tipo.codigo == "elecciones":
        consulta = DestinatarioPersonal.objects.filter(pk=1)
        jefatura = (consulta.select_for_update() if bloquear else consulta).first()
    documentacion = expediente_services.consultar_documentacion(concurso, controles=controles, jurados=jurados)
    snapshot = {
        "concurso": instantanea_concurso(concurso),
        "jurados": [participacion(j, ("titulo", "unidad", "representacion", "calidad", "version")) for j in jurados],
        "aspirantes": [participacion(a, ("email", "expediente_inscripcion", "version")) for a in aspirantes],
        "resultados": cuadro_resultados(concurso, bloquear=bloquear) if tipo.codigo == "dictamen" else {},
        "controles_versiones": [{"id": c.pk, "version": c.version, "verificado": c.verificado,
                                   "fojas": c.fojas, "partida_principal": c.partida_principal,
                                   "actividad_presupuestaria": c.actividad_presupuestaria} for c in controles],
        "actuaciones_verificadas": [
            {"requisito": c.requisito, "fojas": c.fojas, "version": c.version,
             "partida_principal": c.partida_principal, "actividad_presupuestaria": c.actividad_presupuestaria,
             "responsable_id": c.responsable_id,
             "verificado_en": c.verificado_en.isoformat() if c.verificado_en else None}
            for c in documentacion.completos],
        "destinatario": {campo: getattr(destinatario, campo) for campo in (
            "tratamiento", "cargo", "titulo", "nombre", "apellido", "version")} if destinatario else {},
        "destinatario_personal": {campo: getattr(jefatura, campo) for campo in (
            "tratamiento", "cargo", "titulo", "nombre", "apellido", "version")} if jefatura else {},
        "membrete": (lambda m: {"version": m.version, "sha256": m.sha256, "tipo_mime": m.tipo_mime} if m else {})(
            (MembreteInstitucional.objects.select_for_update() if bloquear else MembreteInstitucional.objects)
            .filter(pk=1).first()) if tipo.codigo in ("jurados", "elecciones", "apunsj") else {},
        "fuente": {"archivo": tipo.fuente, "sha256": hashlib.sha256(fuente_original(tipo).read_bytes()).hexdigest()}
            if tipo.fuente and fuente_original(tipo).is_file() else {},
        "plantilla_version": tipo.version,
    }
    return snapshot, controles, jurados, destinatario


def huella_fuentes(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


@transaction.atomic
def preparar_revision(*, concurso_id, tipo_codigo, usuario, datos, huella_esperada=None):
    if not usuario.has_perms(PERMISOS_GENERACION):
        raise PermissionDenied
    tipo = POR_CODIGO.get(tipo_codigo)
    if tipo is None:
        raise ValidationError("Tipo de documento desconocido.")
    concurso = Concurso.objects.select_for_update().get(pk=concurso_id)
    snapshot, controles, jurados, destinatario = fuentes_actuales(concurso, tipo, bloquear=True)
    if not huella_esperada or huella_esperada != huella_fuentes(snapshot):
        raise ValidationError("Los datos cambiaron desde la revisión. Volvé a abrir el documento antes de generar.")
    faltantes = []
    if tipo.fuente and not snapshot["fuente"]:
        faltantes.append(f"Modelo original no disponible: {tipo.fuente}.")
    habilitacion = expediente_services.habilitacion_convocatoria(concurso, controles=controles, jurados=jurados)
    if tipo.codigo == "convocatoria":
        faltantes.extend(habilitacion.faltantes)
        faltantes.extend(faltantes_convocatoria(concurso, controles))
    else:
        faltantes.extend(faltantes_generales(concurso))
    faltantes.extend(faltantes_jurisdiccion_oficios(concurso, tipo))
    if tipo.codigo in ("jurados", "dictamen", "designacion"):
        faltantes.extend(habilitacion.pendientes_jurado)
    faltantes.extend(faltantes_antecedentes(concurso, tipo, controles=controles, aspirantes=snapshot["aspirantes"]))
    if tipo.codigo == "dictamen":
        faltantes.extend(faltantes_resultados(snapshot["resultados"]))
    if tipo.codigo == "desierto_inscriptos":
        faltantes.extend(faltantes_desierto_inscriptos(concurso, instantanea=snapshot))
    if tipo.codigo == "apunsj":
        faltantes.extend(faltantes_destinatario(destinatario))
        if not concurso.resolucion_convocatoria:
            faltantes.append("Registrar la resolución oficial de convocatoria en Datos del concurso antes de solicitar el veedor.")
    if tipo.codigo == "elecciones":
        if concurso.modalidad != "cerrado_interno":
            faltantes.append("El oficio fuente solo está aprobado para Concurso Cerrado Interno.")
        jefatura = snapshot["destinatario_personal"]
        if not jefatura:
            faltantes.append("Configurar la jefatura del Departamento de Personal antes de generar el oficio.")
        if not concurso.causa_vacancia or (concurso.causa_vacancia != "nuevo" and not concurso.fecha_baja):
            faltantes.append("Completar causa y fecha de vacancia en Datos del concurso.")
        if concurso.causa_vacancia == "traslado" and not concurso.acto_vacancia:
            faltantes.append("Completar el acto administrativo que acredita el traslado del cargo.")
        if concurso.causa_vacancia == "otra" and not concurso.detalle_vacancia:
            faltantes.append("Completar el antecedente acreditado de vacancia (otra causa).")
        if concurso.causa_vacancia in ("concurso", "efectivizacion", "jubilacion", "renuncia", "fallecimiento") and not concurso.ex_titular:
            faltantes.append("Completar ex titular del cargo.")
    if tipo.codigo in ("elecciones", "apunsj") and not snapshot["membrete"]:
        faltantes.append("Cargar el membrete vigente en Configuración institucional antes de generar el oficio.")
    if tipo.codigo == "jurados" and not concurso.resolucion_convocatoria:
        faltantes.append("Registrar la resolución oficial de convocatoria en Datos del concurso antes de notificar a los jurados.")
    if tipo.codigo == "jurados" and not snapshot["membrete"]:
        faltantes.append("Cargar el membrete vigente en Configuración institucional antes de generar las notificaciones.")
    if faltantes:
        raise ValidationError(faltantes)
    from .forms import GeneracionForm
    form = GeneracionForm({**datos, "huella_esperada": huella_esperada}, tipo=tipo, concurso=concurso,
                          acotado=concurso.modalidad == "acotado" and tipo.codigo != "apunsj")
    if not form.is_valid():
        raise ValidationError([f"{campo}: {', '.join(errores)}" for campo, errores in form.errors.items()])
    limpios = form.cleaned_data
    if concurso.version != limpios["version_concurso"] or (tipo.codigo == "apunsj" and
            destinatario.version != limpios["version_destinatario"]):
        raise ValidationError("Los datos cambiaron desde la revisión. Volvé a abrir el documento antes de generar.")
    if tipo.codigo == "desierto_inscriptos":
        from participantes.evaluaciones import diagnostico_sin_ganador
        # Reusar la regla de progresión, solo para un llamado nuevo. No se altera la modalidad actual.
        diagnostico = diagnostico_sin_ganador(
            concurso, cuadro={"cantidad_aspirantes": 0}, acta_inscriptos_completa=True)
        if not diagnostico or not diagnostico["siguiente_codigo"]:
            raise ValidationError("No es posible determinar una modalidad para el nuevo llamado.")
        snapshot["nuevo_llamado"] = {
            "modalidad": diagnostico["siguiente_codigo"],
            "nombre": diagnostico["siguiente_nombre"],
            "fundamento": "Artículos 4 y 45 del Anexo de la Ordenanza 33/10-CS (texto actualizado)",
        }
    snapshot["complementarios"] = {k: (v.isoformat() if isinstance(v, date) else v)
        for k, v in limpios.items() if not k.startswith("version_") and k != "huella_esperada"}
    snapshot["pendientes"] = []
    if tipo.codigo in ("jurados", "elecciones", "apunsj"):
        # La fecha efectiva de preparación se captura en la generación y queda histórica.
        hoy = timezone.localdate()
        meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                 "agosto", "septiembre", "octubre", "noviembre", "diciembre")
        snapshot["complementarios"]["lugar_fecha"] = (
            f"San Juan, {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}")
        if tipo.codigo in ("jurados", "apunsj"):
            snapshot["complementarios"]["res_convocatoria"] = concurso.resolucion_convocatoria
    return snapshot


@transaction.atomic
def generar(*, concurso_id, tipo_codigo, usuario, version_concurso, version_destinatario=0,
            revision_administrativa=False, complementarios=None, huella_esperada=None):
    snapshot = preparar_revision(concurso_id=concurso_id, tipo_codigo=tipo_codigo, usuario=usuario,
        datos={**(complementarios or {}), "version_concurso": version_concurso,
               "version_destinatario": version_destinatario, "revision_administrativa": revision_administrativa},
        huella_esperada=huella_esperada)
    tipo = POR_CODIGO[tipo_codigo]
    if tipo.codigo in ("jurados", "elecciones", "apunsj"):
        membrete = MembreteInstitucional.objects.select_for_update().get(pk=1)
        if membrete.sha256 != snapshot["membrete"]["sha256"]:
            raise ValidationError("El membrete cambió. Volvé a abrir la revisión.")
        imagen_membrete = bytes(membrete.contenido)
    if tipo.codigo == "jurados":
        salida = BytesIO()
        snapshot["archivos"] = []
        with ZipFile(salida, "w", compression=ZIP_DEFLATED) as archivo:
            for indice, jurado in enumerate(snapshot["jurados"], 1):
                contenido_nota = renderizar(tipo, {**snapshot, "jurado_actual": jurado}, membrete=imagen_membrete)
                nombre = nombre_miembro(indice)
                archivo.writestr(nombre, contenido_nota)
                snapshot["archivos"].append({"indice": indice, "nombre": nombre, "jurado_id": jurado["id"],
                    "representacion": jurado["representacion"], "calidad": jurado["calidad"],
                    "sha256": hashlib.sha256(contenido_nota).hexdigest()})
        contenido = salida.getvalue()
    else:
        contenido = renderizar(tipo, snapshot, membrete=imagen_membrete if tipo.codigo in ("elecciones", "apunsj") else None)
    return GeneracionDocumento.objects.create(
        concurso_id=concurso_id, tipo=tipo.codigo, plantilla_version=tipo.version, instantanea=snapshot,
        contenido=contenido, sha256=hashlib.sha256(contenido).hexdigest(), generado_por=usuario,
    )
