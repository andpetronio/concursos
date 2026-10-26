# SDD-006 · Fase 3D-2: Listados, formularios e historiales

**Alcance:** segunda pasada de refinamiento UI/UX sobre la fase 3D-1. No implementa todavía automatización de etapa ni cambios documentales.

## Mejoras incorporadas

- **Listado de concursos:** cargo destacado, expediente identificable, acción de limpiar filtros junto a la búsqueda y mensajes distintos para ausencia de concursos y búsqueda sin coincidencias. Se conserva la consulta Django y la paginación actuales.
- **Formulario de participantes:** nombre y apellido de la persona vinculada con jerarquía visual, DNI secundario; sigue diferenciada la edición de participación frente a la corrección de los datos compartidos de Persona.
- **Historial documental:** en el requisito de afectación presupuestaria se ven los valores anteriores y nuevos de **PPAL y ACTIV**, recuperados de los JSON auditados. En los otros veinte requisitos no se agrega columna presupuestaria. No se modifica ningún historial.
- **Pantallas institucionales:** navegación de retorno consistente y título exacto «Membrete institucional»; vista previa sin estilo inline y con límites responsive.
- **Login:** oculto el recuadro vacío que decía «Espacio reservado para ilustración abstracta». La ilustración institucional propiamente dicha continúa pendiente de generar/aprobar.

## Compatibilidad

- Sin cambios en modelos, migraciones, permisos, validadores, estado/etapa administrativa, JavaScript, cookies o guardado automático.
- Un ajuste en una prueba de listado por su nueva distinción entre vacío y sin resultados.
- Una prueba adicional para verificar que el historial presupuestario muestra PPAL y ACTIV antes/después.

## Verificaciones y pendientes

- Código Python: comprobación sintáctica de los dos archivos de pruebas modificados.
- CSS: análisis con `tinycss2` sin errores; Chromium sobre fixture sintética a 1280 y 360 px, ambos sin desbordamiento horizontal. No equivale a QA de pantallas reales Django.
- Parche: comprobación `git apply --check` sobre copia independiente de la versión 3D-1.
- **Pendiente en el equipo del usuario:** ejecutar Django/PostgreSQL con `manage.py check`, `manage.py test concursos participantes expedientes documentos core` y revisar pantallas reales de listado, edición de participante, historial de afectación, configuración y login.
- **Siguiente hito funcional:** fase 4, avance automático de la *etapa documental* Preparación → Convocatoria al completar los cinco requisitos previos. No equivale al estado administrativo «Convocado» y requiere validación de concurrencia, historial y corrección manual.
