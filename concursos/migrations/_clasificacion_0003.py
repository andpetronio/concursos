"""Instantánea inmutable para la migración 0003; no importar catálogos de ejecución."""

AGRUPAMIENTOS = {
    "01": "Administrativo", "2A": "Técnico-profesional", "2B": "Técnico-profesional",
    "03": "Mantenimiento, producción y servicios generales",
    "4A": "Asistencial", "4B": "Asistencial", "4C": "Asistencial", "4D": "Asistencial",
}
MATRIZ = {
    "01": {"Mayor": (1, 2, 3), "Intermedio": (4, 5), "Inicial": (6, 7)},
    "2A": {"Mayor": (1, 2, 3), "Intermedio": (4, 5)},
    "2B": {"Mayor": (2, 3), "Intermedio": (4, 5), "Inicial": (6, 7)},
    "03": {"Mayor": (2, 3), "Intermedio": (4, 5), "Inicial": (6, 7)},
    "4A": {"Mayor": (2, 3), "Intermedio": (4, 5), "Inicial": (6,)},
    "4B": {"Mayor": (2, 3), "Intermedio": (4, 5), "Inicial": (6, 7)},
    "4C": {"Mayor": (1, 2, 3), "Intermedio": (4, 5), "Inicial": (6, 7)},
    "4D": {"Mayor": (3,), "Intermedio": (4, 5), "Inicial": (6, 7)},
}
MODALIDADES = {"cerrado_interno": "Cerrado Interno", "cerrado_general": "Cerrado General",
               "abierto": "Abierto", "acotado": "Acotado"}
CAMPOS = ("modalidad", "agrupamiento", "categoria", "tramo")


def normalizar(valor):
    return " ".join(valor.split()).casefold()


def convertir(datos):
    modalidades = {normalizar(valor): codigo for codigo, label in MODALIDADES.items() for valor in (codigo, label)}
    modalidad = modalidades.get(normalizar(datos["modalidad"]))
    candidatos = [codigo for codigo, label in AGRUPAMIENTOS.items()
                  if normalizar(datos["agrupamiento"]) in
                  (normalizar(codigo), normalizar(label), normalizar(f"{codigo} — {label}"))]
    if not modalidad or len(candidatos) != 1:
        raise ValueError("modalidad o agrupamiento desconocido/ambiguo")
    codigo = candidatos[0]
    categoria = datos["categoria"].strip()
    tramo = next((nombre for nombre, categorias in MATRIZ[codigo].items()
                  if categoria in [str(numero) for numero in categorias]), None)
    if not tramo or (datos["tramo"].strip() and normalizar(datos["tramo"]) != normalizar(tramo)):
        raise ValueError("categoría o tramo inconsistente")
    return {"modalidad": modalidad, "agrupamiento": codigo, "categoria": categoria, "tramo": tramo}


def migrar(apps, schema_editor):
    Concurso = apps.get_model("concursos", "Concurso")
    registros = Concurso.objects.using(schema_editor.connection.alias).all()
    cambios = []
    pendientes = []
    for registro in registros.iterator():
        anterior = {campo: getattr(registro, campo) for campo in CAMPOS}
        try:
            cambios.append((registro.pk, anterior, convertir(anterior)))
        except ValueError as error:
            pendientes.append(f"concurso {registro.pk}: {error}")
    if pendientes:
        # Preflight completo: ningún registro se transforma antes de resolver todos.
        raise RuntimeError("Clasificación pendiente de revisión administrativa. No se convirtió ningún concurso: "
                           + "; ".join(pendientes))
    for pk, anterior, nuevos in cambios:
        Concurso.objects.using(schema_editor.connection.alias).filter(pk=pk).update(
            **nuevos, clasificacion_anterior=anterior,
        )


def revertir(apps, schema_editor):
    Concurso = apps.get_model("concursos", "Concurso")
    for registro in Concurso.objects.using(schema_editor.connection.alias).all().iterator():
        anterior = registro.clasificacion_anterior
        if not anterior:
            continue  # Alta posterior: los campos de texto anteriores admiten los códigos.
        actual = {campo: getattr(registro, campo) for campo in CAMPOS}
        if actual == convertir(anterior):
            Concurso.objects.using(schema_editor.connection.alias).filter(pk=registro.pk).update(**anterior)
        # No sobrescribir decisiones explícitas posteriores con una instantánea vieja.
