from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from concursos.choices import EstadoConcurso
from participantes.models import Jurado

from .catalogo import REQUISITOS, SECCIONES
from .models import CambioControlDocumental, ControlDocumental, SeguimientoDocumental, CambioEtapaDocumental


def inicializar_controles(concurso):
    """Creación explícita dentro de la transacción de alta del concurso."""
    ControlDocumental.objects.bulk_create([
        ControlDocumental(concurso=concurso, requisito=r.codigo) for r in REQUISITOS
    ])
    SeguimientoDocumental.objects.create(concurso=concurso)


@transaction.atomic
def actualizar_etapa(*, concurso_id, etapa, usuario, version_esperada):
    if not usuario.has_perms(("concursos.view_concurso", "expedientes.change_controldocumental")):
        raise PermissionDenied
    seguimiento = SeguimientoDocumental.objects.select_for_update().get(concurso_id=concurso_id)
    if seguimiento.version != version_esperada:
        raise ValidationError("Otro operador modificó la etapa documental. Volvé a abrir la ficha antes de guardar.")
    anterior = seguimiento.etapa
    seguimiento.etapa = etapa
    seguimiento.full_clean()
    if anterior == etapa:
        return seguimiento
    seguimiento.version += 1
    seguimiento.save(update_fields=["etapa", "version"])
    CambioEtapaDocumental.objects.create(seguimiento=seguimiento, usuario=usuario,
                                        anterior=anterior, nueva=etapa, version=seguimiento.version)
    return seguimiento


def instantanea(control):
    return {
        "verificado": control.verificado, "fojas": control.fojas, "observaciones": control.observaciones,
        "responsable_id": control.responsable_id,
        "verificado_en": control.verificado_en.isoformat() if control.verificado_en else None,
    }


@transaction.atomic
def actualizar_control(*, concurso_id, control_id, datos, usuario, version_esperada):
    if not usuario.has_perms(("concursos.view_concurso", "expedientes.change_controldocumental")):
        raise PermissionDenied
    control = ControlDocumental.objects.select_for_update().get(pk=control_id, concurso_id=concurso_id)
    if control.version != version_esperada:
        raise ValidationError("Otro operador modificó este control. Volvé a abrir la ficha y revisá los datos antes de guardar.")
    anterior = instantanea(control)
    for campo in ("verificado", "fojas", "observaciones"):
        if campo in datos:
            setattr(control, campo, datos[campo])
    control.full_clean()
    if instantanea(control) == anterior:
        return control
    if control.verificado:
        control.responsable = usuario
        control.verificado_en = timezone.now()
    # Al desmarcar se conserva la última verificación histórica; el evento registra la revocación.
    control.actualizado_por = usuario
    control.version += 1
    control.save()
    CambioControlDocumental.objects.create(
        control=control, usuario=usuario, version=control.version, anterior=anterior, nuevo=instantanea(control),
    )
    return control


@dataclass(frozen=True)
class HabilitacionConvocatoria:
    pendientes_documentales: tuple
    pendientes_jurado: tuple
    pendientes_datos: tuple

    @property
    def habilitado(self):
        return not self.faltantes

    @property
    def faltantes(self):
        return self.pendientes_documentales + self.pendientes_jurado + self.pendientes_datos


def habilitacion_convocatoria(concurso, *, controles=None, jurados=None):
    controles = list(controles) if controles is not None else list(concurso.controles_documentales.all())
    jurados = list(jurados) if jurados is not None else list(concurso.jurados.select_related("persona"))
    por_codigo = {control.requisito: control for control in controles}
    documentos = tuple(r.nombre for r in REQUISITOS if r.seccion == "preparacion"
                       and (r.codigo not in por_codigo or not por_codigo[r.codigo].completo))
    plazas = {(j.representacion, j.calidad): j for j in jurados}
    faltantes_jurado = []
    for representacion, nombre in Jurado.Representacion.choices:
        for calidad, caracter in Jurado.Calidad.choices:
            jurado = plazas.get((representacion, calidad))
            if jurado is None:
                faltantes_jurado.append(f"Jurado de {nombre}: falta {caracter.lower()}.")
                continue
            campos = {"apellido": jurado.persona.apellido, "nombre": jurado.persona.nombre,
                      "DNI": jurado.persona.dni, "título": jurado.titulo, "unidad": jurado.unidad}
            vacios = [campo for campo, valor in campos.items() if not valor.strip()]
            if vacios:
                faltantes_jurado.append(f"Jurado de {nombre}, {caracter.lower()}: completar {', '.join(vacios)}.")
    datos = []
    try:
        concurso.full_clean()
    except ValidationError as error:
        for campo in getattr(error, "message_dict", {"__all__": error.messages}):
            etiqueta = concurso._meta.get_field(campo).verbose_name if campo != "__all__" else "datos generales"
            datos.append(f"Revisar {etiqueta} del concurso.")
    for campo in concurso.DATOS_EDITABLES:
        definicion = concurso._meta.get_field(campo)
        if not definicion.blank and not str(getattr(concurso, campo)).strip():
            aviso = f"Revisar {definicion.verbose_name} del concurso."
            if aviso not in datos:
                datos.append(aviso)
    return HabilitacionConvocatoria(documentos, tuple(faltantes_jurado), tuple(datos))


def sugerencia_estado(concurso, controles):
    """Solo propone un evento inequívoco; no ejecuta cambios administrativos."""
    if concurso.estado not in (EstadoConcurso.PREPARACION, EstadoConcurso.CONVOCADO, EstadoConcurso.EN_CURSO):
        return None
    if any(c.requisito == "dictamen" and c.completo for c in controles):
        return EstadoConcurso.CON_DICTAMEN
    return None


def advertencias_secuencia(controles):
    por_codigo = {c.requisito: c for c in controles}
    advertencias = []
    inicio = next(i for i, r in enumerate(REQUISITOS) if r.codigo == "acta_inscriptos")
    secuencia = REQUISITOS[inicio:]
    for indice, requisito in enumerate(secuencia):
        control = por_codigo.get(requisito.codigo)
        if not control or not control.verificado:
            continue
        previos = [r.nombre for r in secuencia[:indice]
                   if r.codigo not in por_codigo or not por_codigo[r.codigo].completo]
        if previos:
            advertencias.append(f"{requisito.nombre}: documentación precedente pendiente: {', '.join(previos)}.")
    return tuple(advertencias)


@dataclass(frozen=True)
class DocumentacionConcurso:
    controles: tuple
    habilitacion: HabilitacionConvocatoria
    advertencias: tuple
    sugerencia: str | None
    seguimiento: SeguimientoDocumental

    @property
    def total(self):
        return len(REQUISITOS)

    @property
    def verificados(self):
        return tuple(c for c in self.controles if c.verificado)

    @property
    def completos(self):
        return tuple(c for c in self.controles if c.completo)

    @property
    def pendientes(self):
        completos = {c.requisito for c in self.completos}
        return tuple(r for r in REQUISITOS if r.codigo not in completos)

    @property
    def secciones_exigibles(self):
        codigos = [codigo for codigo, _ in SECCIONES]
        return codigos[:codigos.index(self.seguimiento.etapa) + 1]

    @property
    def pendientes_exigibles(self):
        return tuple(r for r in self.pendientes if r.seccion in self.secciones_exigibles)

    @property
    def no_registrados_futuros(self):
        return tuple(r for r in self.pendientes if r.seccion not in self.secciones_exigibles)

    @property
    def fojas(self):
        return {c.requisito: c.fojas for c in self.controles if c.fojas}


def consultar_documentacion(concurso, *, controles=None, jurados=None):
    """Consulta reutilizable para ficha y futura SDD-005, sin escrituras ni generación."""
    controles = tuple(controles) if controles is not None else tuple(
        concurso.controles_documentales.select_related("responsable", "actualizado_por")
    )
    orden = {r.codigo: posicion for posicion, r in enumerate(REQUISITOS)}
    controles = tuple(sorted(controles, key=lambda control: orden[control.requisito]))
    return DocumentacionConcurso(
        controles, habilitacion_convocatoria(concurso, controles=controles, jurados=jurados),
        advertencias_secuencia(controles), sugerencia_estado(concurso, controles),
        SeguimientoDocumental.objects.get(concurso=concurso),
    )
