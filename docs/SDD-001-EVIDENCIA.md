# Evidencia de entrega SDD-001

Fecha: 22/10/2026. Alcance: únicamente `001-fundaciones.md`, autorizada. Implementación y verificaciones backend terminadas; validación visual real pendiente por indisponibilidad de navegador. No se declara aprobación de SDD-002 ni se modifica su estado.

## Archivos incorporados/modificados

- Arranque: `manage.py`, `Dockerfile`, `compose.yaml`, `requirements.txt`, `.env.example`, `.dockerignore`; ampliación de `.gitignore`.
- Configuración: `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/test_settings.py` (diagnóstico SQLite explícito).
- Base Django: `core/__init__.py`, `core/apps.py`, `core/admin.py`, `core/forms.py`, `core/models.py`, `core/middleware.py`, `core/session_activity.py`, `core/views.py`, `core/urls.py`.
- Migraciones: `core/migrations/__init__.py`, `core/migrations/0001_initial.py`.
- Pruebas: `core/tests/__init__.py`, `core/tests/test_auth.py`, `core/tests/test_concurrency.py`.
- Templates: `templates/base.html`, `templates/layouts/auth.html`, `templates/layouts/private.html`, `templates/registration/login.html`, `templates/core/dashboard.html`, `templates/core/forbidden.html`, `templates/admin/base_site.html`.
- Componentes: `templates/components/{brand,button,card,field,messages,navigation,page_header}.html`.
- Recursos: `static/css/tokens.css`, `static/css/app.css`, `static/css/admin-adapter.css`, `static/js/session.js`.
- Guía y evidencia: `README.md`, este archivo.

Se detectaron y leyeron las cuatro skills del repositorio: `sdd-entrega`, `django-calidad`, `ui-consistente` y `sesion-segura`. No se necesitó reemplazar skills ausentes. Los agentes configurados estuvieron disponibles y se utilizaron.

## Decisiones técnicas

- Auth, Forms, sesiones, CSRF y permisos de Django nativos. Un login común inicializa el reloj, incluido el ingreso al admin; sin registro público ni gestión de usuarios propia.
- Único modelo nuevo: reloj asociado a Session mediante OneToOne. Conserva la última actividad en PostgreSQL, fuera del JSON de sesión. Middleware con transacción/lock por sesión antes de vista o renovación; el cambio nativo de contraseña traslada el reloj sin alterar su fecha.
- Inactividad a partir de la última señal reconocida en servidor, límite inclusivo de 1800 s. La renovación revalida el plazo para cubrir el cruce entre middleware y vista. Requests normales, estado, polling y assets no renuevan. Navegación intencional y eventos JS visibles se describen con sus límites en README. No son prueba criptográfica de presencia humana.
- Tokens compartidos y layouts diferenciados. Adapter acotado para el DOM del admin nativo; deshabilitado su tema oscuro para conservar identidad blanco/naranja. Sin componentes especulativos para pantallas de fases futuras.
- Python 3.13.17 en imagen fijada por digest, Django 5.2.18, psycopg 3.3.6 y PostgreSQL 17.11. Dependencias Python directas/transitivas fijadas. Fuentes oficiales enlazadas en README.
- Compose local, DB sin puerto publicado, web solo en loopback y volumen persistente. Migraciones explícitas. Sin configuración de despliegue de producción.

## Comandos y resultados efectivos

Ejecutados desde PowerShell/Windows 11, con Docker Desktop Linux. Los comandos de Compose usan el entorno local, sin imprimir credenciales.

| Comando | Resultado real |
|---|---|
| `docker compose config --quiet` | Exit 0 |
| `docker compose up -d --build` y reconstrucción posterior de `web` | Imágenes construidas, db healthy y web iniciado |
| `docker compose exec -T web python manage.py migrate --noinput` | Migraciones nativas y `core.0001_initial` aplicadas OK |
| `docker compose exec -T web python manage.py check` | `System check identified no issues (0 silenced).` |
| `docker compose exec -T web python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `docker compose exec -T web python manage.py migrate --check` | Exit 0, sin pendientes |
| `docker compose exec -T web python manage.py test -v 1` después de corregir revisiones | **`Ran 25 tests in 7.952s` / `OK`**, sin skips, PostgreSQL 17.11 |
| `docker compose exec -T web python -m pip check` | `No broken requirements found.` |
| `docker compose exec -T web python --version` | `Python 3.13.17` |
| Node del runtime local: `node --check static/js/session.js` | Exit 0; valida sintaxis, no ejecución en navegador |
| Diagnóstico local: `.venv/Scripts/python.exe manage.py test --settings=config.test_settings -v 1` | 25 tests, `OK (skipped=1)`; se omite lock PostgreSQL. No sustituye la suite del contenedor |
| HTTP real con `urllib.request.urlopen`, dentro de web | `/health/`, `/ingresar/`, `/static/css/app.css`, `/static/js/session.js`: **200** |
| Comprobación `Path('/app/.env').exists()` dentro de web | False; el archivo local de secretos no se incorporó a la imagen |
| Consulta de cantidad de usuarios persistentes | **0**; no se crearon cuentas demo |
| `docker compose ps` | db healthy, web Up, `127.0.0.1:8000->8000/tcp` |

Las bases de test se crearon desde cero, aplicaron todas las migraciones y se eliminaron por el runner Django. El volumen operativo se conserva; no se borraron datos persistentes. La primera pasada sobre PostgreSQL tuvo 21 tests; la siguiente 22; la final posterior a correcciones tuvo los 25 informados.

La suite cubre login válido/inválido, redirección `next` segura, rotación/cookies, anónimos, CSRF de login/logout/actividad, GET de logout sin destrucción, POST de logout con invalidación, 1799/1800/1801 s, renovación1799, rechazo de renovación vencida y cruce1799→1800 dentro del mismo request, POST admin vencido sin crear datos, solicitudes automáticas/precargas, health y estado sin renovación, throttling30s, pestañas compartidas, sesión sin reloj, permisos staff, recorrido anónimo-admin-login-admin, cambio de contraseña propio y conservación del reloj. El test concurrente usa dos conexiones reales y verifica espera del lock antes de observar la última marca.

Se resolvieron restricciones iniciales: `python`/`py` del PATH eran alias no ejecutables; se utilizó el Python 3.12.14 del runtime local para crear `.venv`. La primera descarga pip fue bloqueada por sockets del sandbox y se ejecutó con aprobación de la herramienta. Docker inicialmente no tenía motor activo; se inició Docker Desktop y después se verificaron servicios y suite reales. Un intento inicial de generar claves mediante una API .NET no disponible se sustituyó por `secrets` de Python. Ninguna de estas comprobaciones fallidas se contabiliza como prueba aprobada.

## Revisiones independientes de solo lectura

| Revisor | Hallazgo confirmado | Respuesta y confirmación |
|---|---|---|
| `revisor_django` | El flujo anónimo al admin volvía a su login y daba403 a staff | Se conserva el destino original hacia login común. Regresión end-to-end agregada; revisor confirmó corrección y ejecutó esa regresión en memoria |
| `revisor_django` | Cambiar contraseña propia eliminaba reloj por cascada al rotar Session | Se traslada `last_activity` a la nueva clave sin renovar. Regresión agregada; revisor confirmó y ejecutó el caso en memoria |
| `auditor_ui` | Tema oscuro heredado del admin dejaba contraste insuficiente sobre blanco | Anulado bloque `dark-mode-vars`. Revisor renderizó plantilla y confirmó ausencia de `theme.js`/`dark_mode.css` y presencia de tokens/adapter |
| `auditor_seguridad` | Cruce del límite entre middleware y endpoint podía renovar a los1800s | Se comparte regla `is_expired` y se revalida en endpoint. Test de cruce agregado. Auditor reprodujo401 y cero renovaciones con código corregido |

Los tres revisaron el código corregido sin editar archivos; no reportaron defectos residuales demostrables. Los 25 tests finales de PostgreSQL se ejecutaron por el agente principal después de integrar las correcciones; su salida se comunicó a los revisores. No se presenta una revisión estática como validación visual o ejecución de JS en un navegador.

## QA y límites pendientes

- [x] Solo fundaciones; sin concursos, participantes, checklist, DOCX, CoPla ni datos de negocio.
- [x] Componentes/tokens compartidos, errores de formulario y etiquetas revisados en código/render.
- [x] Sin validaciones duplicadas de negocio ni capas especulativas; regla de vencimiento compartida.
- [x] Auth, permisos, CSRF, logout y límites de sesión probados.
- [x] Migraciones desde cero, checks y pruebas dentro de contenedor PostgreSQL.
- [x] Revisiones independientes disponibles realizadas y hallazgos corregidos.
- [x] README con instrucciones macOS y PowerShell, creación de usuario y pruebas.
- [x] Sin datos personales reales, dumps, commits, pushes, deploys ni cambios en CoPla. `.env` local ignorado conserva las claves aleatorias del entorno ya iniciado; nunca se imprime ni se incluye en imagen. No se incorporan secretos a archivos destinados a versionado.
- [ ] Revisión visual real de login/error/panel/admin a **360/768/1280 px**, teclado/foco, responsive y JS real.

**Limitación exacta:** `cua.getState()` devolvió `apps: []` y `browsers: []`. El intento `cua.createBrowserTab('iab', 'http://127.0.0.1:8000/ingresar/', ...)` devolvió **`Browser is not available: iab`**. No hubo screenshots ni verificación visual. La revisión CSS, los renders y HTTP200 no sustituyen esa comprobación. Tampoco se ejecutaron comandos desde un equipo macOS; la guía utiliza la misma interfaz de Compose y diferencias de shell documentadas.

No se ejecutó `createsuperuser` sobre la base operativa: requiere que el operador elija sus credenciales. Los servicios quedaron iniciados y se puede ejecutar `docker compose exec web python manage.py createsuperuser`, luego acceder a <http://127.0.0.1:8000/>. Para futuras instalaciones, seguir README. No se inicializó Git: el directorio recibido no tenía `.git`; no hay un diff/status Git verificable.

Entrega detenida en SDD-001. Queda la verificación visual indicada y la aprobación del operador; no se avanza a SDD-002.
