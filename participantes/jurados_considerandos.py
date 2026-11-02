"""F4M.1: vista previa de antecedentes del jurado, sin emitir actos administrativos.

Lee ActuacionJurado (F4L). No modifica participantes, expedientes ni DOCX.
Las fechas de actuación se usan para ordenar antecedentes, NO para presumir
la fecha de efectos de una designación o un cese.
"""

from dataclasses import dataclass
from datetime import date


REPRESENTACIONES = {
    "dependencia": "de la autoridad de la dependencia convocante",
    "rectorado": "del Rectorado",
    "personal": "del personal de la dependencia",
}
CALIDADES = {"titular": "titular", "suplente": "suplente"}


@dataclass(frozen=True)
class BloqueAntecedentesJurado:
    """Texto propuesto para revisión. No acredita por sí mismo las actuaciones."""

    resolucion: str
    fecha_resolucion: date
    identificadores_actuacion: tuple
    considerandos: tuple[str, ...]
    faltantes: tuple[str, ...]

    @property
    def completo_para_revision(self):
        """Los datos permiten revisar el texto; NO equivale a acto acreditado."""
        return not self.faltantes


@dataclass(frozen=True)
class VistaPreviaAntecedentesJurado:
    bloques: tuple[BloqueAntecedentesJurado, ...]
    advertencias: tuple[str, ...]

    @property
    def completa_para_revision(self):
        return all(b.completo_para_revision for b in self.bloques) and not self.advertencias


def _valor(obj, nombre, predeterminado=None):
    return getattr(obj, nombre, predeterminado) if obj is not None else predeterminado


def _nombre(jurado):
    persona = _valor(jurado, "persona")
    nombre = str(_valor(persona, "nombre", "") or "").strip()
    apellido = str(_valor(persona, "apellido", "") or "").strip()
    return f"{nombre} {apellido}".strip()


def _label_representacion(valor):
    return REPRESENTACIONES.get(valor, "")


def _faltantes_base(acto):
    faltantes = []
    if not str(_valor(acto, "resolucion", "") or "").strip():
        faltantes.append("Número de resolución rectoral")
    if not _valor(acto, "fecha_actuacion"):
        faltantes.append("Fecha de resolución rectoral")
    if not str(_valor(acto, "fojas", "") or "").strip():
        faltantes.append("Fojas de la resolución rectoral")
    if not _nombre(_valor(acto, "jurado")):
        faltantes.append("Identificación del integrante del jurado")
    if not _label_representacion(_valor(acto, "representacion")):
        faltantes.append("Representación del jurado")
    return faltantes


def _folio(texto):
    # Las fojas son un dato asentado en el expediente: NO se infieren.
    return str(texto).strip()


def _presentacion_de(acto):
    p = _valor(acto, "antecedente")
    if _valor(p, "tipo") == "presentacion":
        return p
    return None


def _texto_cese(cese, promociones):
    faltantes = _faltantes_base(cese)
    presentacion = _presentacion_de(cese)
    if not presentacion:
        faltantes.append("Presentación de origen vinculada al cese")
        return (), faltantes
    if not _folio(_valor(presentacion, "fojas", "") or ""):
        faltantes.append("Fojas de la presentación")
    motivo = _valor(presentacion, "motivo", "")
    if motivo not in ("excusacion", "recusacion"):
        faltantes.append("Motivo de la presentación (excusación o recusación)")
    calidad = CALIDADES.get(_valor(cese, "calidad_anterior"))
    if not calidad:
        faltantes.append("Carácter anterior del integrante")
    if _valor(presentacion, "fecha_actuacion") and _valor(cese, "fecha_actuacion"):
        if presentacion.fecha_actuacion > cese.fecha_actuacion:
            faltantes.append("La presentación tiene fecha posterior a la resolución")
    nombres_promocion = []
    for promo in promociones:
        faltantes.extend(_faltantes_base(promo))
        if _valor(promo, "calidad_anterior") != "suplente" or _valor(promo, "calidad_nueva") != "titular":
            faltantes.append("La promoción no acredita el paso de suplente a titular")
        if _valor(promo, "resolucion") != _valor(cese, "resolucion") or _valor(promo, "fecha_actuacion") != _valor(cese, "fecha_actuacion"):
            faltantes.append("Cese y promoción no se vinculan al mismo acto administrativo")
        if _valor(promo, "representacion") != _valor(cese, "representacion"):
            faltantes.append("La promoción corresponde a otra representación")
        nombres_promocion.append(_nombre(promo.jurado))
    if faltantes:
        return (), list(dict.fromkeys(faltantes))

    nombre = _nombre(cese.jurado)
    representacion = _label_representacion(cese.representacion)
    presentacion_fojas = _folio(presentacion.fojas)
    res_fojas = _folio(cese.fojas)
    resolucion = cese.resolucion.strip()
    if motivo == "excusacion":
        origen = (
            f"Que a fojas {presentacion_fojas} obra la presentación de excusación formulada "
            f"por {nombre}, en su carácter de miembro {calidad} del Jurado en representación "
            f"{representacion};"
        )
        decision = (
            f"Que mediante Resolución N.º {resolucion}, obrante a fojas {res_fojas}, "
            f"se aceptó dicha excusación y se dispuso el cese de {nombre} como miembro "
            f"{calidad} del Jurado;"
        )
    else:
        # F4L identifica al jurado recusado, NO necesariamente al recurrente.
        origen = (
            f"Que a fojas {presentacion_fojas} obra una presentación de recusación "
            f"respecto de {nombre}, miembro {calidad} del Jurado en representación "
            f"{representacion};"
        )
        decision = (
            f"Que mediante Resolución N.º {resolucion}, obrante a fojas {res_fojas}, "
            f"se dispuso el cese de {nombre} como miembro {calidad} del Jurado "
            f"en relación con dicha recusación;"
        )
    textos = [origen, decision]
    for nuevo in nombres_promocion:
        textos.append(
            f"Que por el mismo acto resolutivo se designó a {nuevo}, hasta entonces "
            f"miembro suplente, como titular del Jurado en representación {representacion};"
        )
    return tuple(textos), []


def _texto_designacion(acto):
    faltantes = _faltantes_base(acto)
    calidad = CALIDADES.get(_valor(acto, "calidad_nueva"))
    if not calidad:
        faltantes.append("Carácter de la nueva designación")
    if faltantes:
        return (), list(dict.fromkeys(faltantes))
    return (
        f"Que mediante Resolución N.º {acto.resolucion.strip()}, obrante a fojas "
        f"{_folio(acto.fojas)}, se designó a {_nombre(acto.jurado)} como miembro "
        f"{calidad} del Jurado en representación {_label_representacion(acto.representacion)};",
    ), []


def preparar_antecedentes_jurado(actuaciones, *, fecha_documento=None):
    """Genera borradores de considerandos de actuaciones *ya registradas* en F4L.

    `fecha_documento` filtra resoluciones posteriores a la fecha del documento.
    NO reconstruye por sí sola la composición histórica ni certifica fojas.
    Conviene pasar un queryset con `select_related('jurado__persona',
    'antecedente')` para evitar consultas N+1.
    """
    actos = list(actuaciones)
    avisos = []
    resolutivos = [a for a in actos if a.tipo in ("cese", "designacion", "promocion")]
    incluidos = [a for a in resolutivos if not fecha_documento or (a.fecha_actuacion and a.fecha_actuacion <= fecha_documento)]
    ceses = [a for a in incluidos if a.tipo == "cese"]
    promociones = [a for a in incluidos if a.tipo == "promocion"]
    designaciones = [a for a in incluidos if a.tipo == "designacion"]
    bloques = []
    usadas = set()

    for cese in ceses:
        presentacion = _presentacion_de(cese)
        vinculadas = [p for p in promociones if presentacion is not None and
                      _valor(p, "antecedente_id", _valor(_valor(p, "antecedente"), "pk")) == _valor(presentacion, "pk")]
        usadas.update(_valor(p, "pk") for p in vinculadas)
        texto, faltantes = _texto_cese(cese, vinculadas)
        ids = tuple(_valor(a, "pk") for a in [cese, *vinculadas])
        bloques.append(BloqueAntecedentesJurado(
            resolucion=_valor(cese, "resolucion", "") or "",
            fecha_resolucion=_valor(cese, "fecha_actuacion"),
            identificadores_actuacion=ids,
            considerandos=texto,
            faltantes=tuple(faltantes),
        ))

    for designacion in designaciones:
        texto, faltantes = _texto_designacion(designacion)
        bloques.append(BloqueAntecedentesJurado(
            resolucion=_valor(designacion, "resolucion", "") or "",
            fecha_resolucion=_valor(designacion, "fecha_actuacion"),
            identificadores_actuacion=(_valor(designacion, "pk"),),
            considerandos=texto,
            faltantes=tuple(faltantes),
        ))

    for promo in promociones:
        if _valor(promo, "pk") not in usadas:
            avisos.append(f"Promoción de jurado sin cese vinculado verificable (actuación {promo.pk}).")

    # Una presentación pendiente se muestra como advertencia, nunca como un cese.
    for acto in actos:
        if acto.tipo == "presentacion" and not _valor(acto, "resuelto_por"):
            avisos.append(f"Presentación pendiente de resolución (actuación {acto.pk}); no se redacta un cese.")

    bloques.sort(key=lambda b: (b.fecha_resolucion or date.max, min((i for i in b.identificadores_actuacion if isinstance(i, int)), default=0)))
    return VistaPreviaAntecedentesJurado(bloques=tuple(bloques), advertencias=tuple(dict.fromkeys(avisos)))
