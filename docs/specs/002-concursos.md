# SDD-002 — Concursos, ficha y estados

**Estado:** AUTORIZADA por pedido del usuario del 22/10/2026. Alcance exclusivo SDD-002.

## Objetivo
Alta, listado, edición y ficha de concursos; estado principal y situación administrativa adicional con cambios auditados.

## Datos mínimos
Expediente, tipo/modalidad, denominación/funciones del cargo, agrupamiento, categoría, tramo, código presupuestario, unidad y dependencia/cadena jerárquica. Los datos generales **no requieren foja**. Mantener fotografía histórica de cargo y estructura.

## Estados
Principales: Preparación (inicial), Convocado, En curso, Con dictamen, Finalizado. Situaciones adicionales: Normal, Impugnado, Suspendido. Cambio manual autorizado con historial usuario-fecha-anterior-nuevo-justificación opcional. El estado no depende mecánicamente del porcentaje de checks. En esta fase las sugerencias automáticas pueden quedar sin implementar hasta existir eventos documentales.

## UI
Listado con filtros por estado y búsqueda por expediente/cargo/código; creación, edición, detalle y estados vacíos. Ficha con navegación futura claramente rotulada, sin enlaces rotos. Mismo diseño de SDD-001.

## Criterios de aceptación
CRUD autenticado y protegido; validación de datos; migraciones; historial de estado comprobable; búsqueda/filtros; pruebas de errores, permisos y estados vacíos; revisión UI.

## Criterios confirmados para esta entrega (22/10/2026)
- Se permiten expedientes repetidos hasta definir su ámbito de unicidad; no imponer unicidad global.
- Tipo/modalidad, agrupamiento, categoría y tramo se registran como texto libre, sin catálogos nuevos.
- Los datos mínimos enumerados son obligatorios. Los campos complementarios quedan fuera de esta fase.
- Permisos Django separados para consultar, crear, editar datos y cambiar estado/situación; no se crean roles de negocio.
- No hay eliminación de concursos en esta fase. «CRUD» se interpreta conforme al objetivo de alta, consulta y edición, preservando el historial.

La definición futura de catálogos, ámbito de unicidad y campos complementarios no se considera resuelta por esta implementación.
