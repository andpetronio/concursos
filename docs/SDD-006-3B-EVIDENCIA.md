# SDD-006 · Fase 3B: entradas, máscaras y límites

Implementación acotada sobre la base acumulada de SDD-006 3C-1/3C-2, APUNSJ v3 y configuración institucional equilibrada. No altera modelos de datos, migraciones ni documentos históricos.

## Alcance

| Campo | Presentación nueva | Validación de servidor y protección histórica |
|---|---|---|
| Expediente del concurso / inscripción | `maxlength=12`, ejemplo `01-758-2026`; sin botón «Agregar guion» ni ayuda extensa | Misma expresión válida de 9 a 12 caracteres, central de 1 a 4 sin relleno. Valores históricos solo se conservan intactos. |
| DNI | Máscara `99.999.999`, `maxlength=10`, entrada como texto; ceros preservados | Normalización persistente a ocho dígitos; separadores anteriores aceptados en POST para compatibilidad. DNI compartido y protección de homónimos intactos. |
| Teléfono de jurado / veedor | Máscara `999-9999999`, `maxlength=11`, opcional | Formulario y `full_clean()` del modelo admiten 10 dígitos o 3-7 con guion. Registros históricos fuera de formato se mantienen si no se modifican. Nunca se rellenan ni se corrigen automáticamente. |
| Código presupuestario del cargo | `maxlength=5` | Formulario y `full_clean()` rechazan más de 5 en valores nuevos/corregidos; códigos históricos más largos pueden conservarse en una edición sin cambios. No se infiere que deban ser numéricos. |

PPAL y ACTIV mantienen su formato propio de dos dígitos. No se impone un límite genérico sobre textos del presupuesto de designación ni sobre filtros de búsqueda. Para expedientes con bloque central de menos de cuatro cifras, el segundo guion se escribe con el teclado; se utiliza `inputmode=text` para que esté disponible en móvil. Al pegar una secuencia numérica completa de entre 7 y 10 dígitos se interpretan los últimos cuatro como año.

## Archivos

- `core/fields.py`, `core/validators.py`, `core/templates/core/widgets/identificador.html`.
- `concursos/forms.py`, `concursos/models.py`, `participantes/forms.py`, `participantes/models.py`.
- `static/js/forms.js`, `static/css/app.css`, `docs/DISEÑO.md`.
- Pruebas de identificadores, participantes, concursos y máscara JavaScript.

## Verificación ejecutada

- `python -m compileall` de las aplicaciones modificadas: correcto.
- `node --check static/js/forms.js`: correcto.
- `node --test core/tests/forms.test.js`: cuatro pruebas correctas.
- `git diff --check` y verificación de aplicación del parche sobre la copia original: correcto.

**Pendiente:** no hay instalación de Django, PostgreSQL ni Docker en el entorno de generación. Ejecutar en el equipo del operador `python manage.py check`, `python manage.py test concursos participantes core expedientes documentos` y controlar manualmente formulario de concurso, altas/ediciones de jurado/veedor/aspirante y preservación de valores previos. No se afirma QA visual en navegador.

No se aplican migraciones ni se modifica la base. No se generan documentos administrativos.
