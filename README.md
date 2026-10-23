# gestion-concursos · UNSJ

Sistema de Gestión Administrativa de Concursos Nodocentes: fundaciones SDD-001, gestión de concursos SDD-002 y participantes SDD-003 (implementación entregada; aceptación del usuario pendiente). Incluye autenticación, vencimiento por inactividad, concursos y registro de jurados, veedores de APUNSJ y aspirantes. El expediente y los actos oficiales continúan fuera de la aplicación. Control documental, DOCX e integración con CoPla corresponden a fases posteriores.

## Requisitos

Docker Desktop iniciado, con Compose y contenedores Linux. En Windows 11, habilitar su backend WSL 2. No hace falta instalar Python ni PostgreSQL en el equipo. Ejecutar los comandos desde la carpeta del proyecto.

Stack: Python 3.13 (imagen fijada por digest; versión verificada 3.13.17), Django 5.2.18 LTS y psycopg 3.3.6, PostgreSQL 17.11. Django aporta auth, sesiones, Forms, CSRF y admin; psycopg es su adaptador PostgreSQL. Dependencias Python fijadas en `requirements.txt`. Las imágenes oficiales reciben sus actualizaciones mediante cambios explícitos de versión/digest.

Fuentes de selección: [Django 5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/), [soporte de Django](https://www.djangoproject.com/download/#supported-versions), [psycopg](https://www.psycopg.org/psycopg3/docs/news.html), [PostgreSQL 17.11](https://www.postgresql.org/docs/17/release-17-11.html).

## Preparación en macOS

```sh
test -f .env || cp .env.example .env
```

## Preparación en Windows 11 / PowerShell

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Si ya existe un `.env` local configurado, conservarlo. Para una instalación nueva, editarlo y reemplazar `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD` por valores aleatorios diferentes. Para generar cada uno:

```sh
docker run --rm python:3.13-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(48))"
```

La clave Django exige al menos 50 caracteres y rechaza el marcador `CAMBIAR`. `.env` queda ignorado y fuera de la imagen Docker. No compartirlo ni incorporarlo a Git. El archivo de ejemplo no contiene credenciales utilizables.

## Arranque (comandos iguales en macOS y PowerShell)

```sh
docker compose config --quiet
docker compose build web
docker compose up -d db
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
docker compose ps
```

Abrir <http://127.0.0.1:8000/>. El login está en `/ingresar/` y el administrador Django en `/admin/`. Crear el usuario inicial con `createsuperuser`; desde el admin se pueden crear cuentas normales, sin permisos de staff para el panel. No hay registro público ni gestor de usuarios propio. Las contraseñas se ingresan por consola interactiva, nunca en argumentos ni en archivos del proyecto.

La base espera su healthcheck antes de arrancar web. PostgreSQL usa el volumen `gestion-concursos_postgres_data`, sin puerto publicado; web se publica solo en `127.0.0.1:8000`. Las migraciones son explícitas. Al modificar código, reconstruir con `docker compose up -d --build web` (no hay montaje del código local).

Para detener conservando datos:

```sh
docker compose stop
```

Para volver a iniciar: `docker compose up -d`. No borrar el volumen. Cambiar `POSTGRES_PASSWORD` en `.env` después de inicializar la base no cambia la contraseña guardada en PostgreSQL.

## Checks y pruebas

Con los servicios iniciados:

```sh
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py migrate --check
docker compose exec web python manage.py test -v 2
docker compose exec web python -m pip check
```

La suite crea y elimina exclusivamente su base de pruebas `test_gestion_concursos`; no usa datos reales. El rol local de PostgreSQL puede crearla. Los casos verifican login válido/inválido, anónimos, redirecciones seguras, rotación y cookies de sesión, CSRF, logout POST/GET, 1799/1800/1801 segundos, renovación anterior al límite, POST del admin vencido sin cambios, polling/precarga/healthchecks sin renovación, frecuencia limitada y pestañas múltiples. La prueba concurrente usa conexiones PostgreSQL separadas y su bloqueo de fila.

SDD-002 agrega pruebas de registro y edición, datos mínimos, expedientes repetidos, estado inicial e historial, cambios manuales y situación independiente, búsqueda/filtros/paginación, errores, permisos separados, CSRF, escrituras vencidas, conflictos entre operadores y rollback si falla la auditoría. La segunda prueba concurrente verifica que dos conexiones que intentan cambiar la misma versión no sobrescriban estados ni dupliquen el historial.

Si Docker no está disponible, existe una alternativa **solo de diagnóstico** con Python 3.12/3.13:

```sh
python -m venv .venv
```

Activar con `source .venv/bin/activate` (macOS) o `.\.venv\Scripts\Activate.ps1` (PowerShell). Luego:

```sh
python -m pip install -r requirements.txt
python manage.py test --settings=config.test_settings
```

Antes definir `DJANGO_SECRET_KEY` en el entorno: `export DJANGO_SECRET_KEY="..."` (macOS) o `$env:DJANGO_SECRET_KEY = "..."` (PowerShell). Esta alternativa usa SQLite en memoria y **no demuestra funcionamiento de PostgreSQL ni sus locks**; la prueba concurrente se omite allí. El archivo `.env` lo interpreta Compose, no Django ejecutado directamente.

## Cómo funciona la inactividad

El login nativo inicializa `SessionActivity`, asociado a la sesión Django. Cada request autenticado toma un lock de fila en PostgreSQL, lee el reloj compartido y, **antes de la vista y de cualquier renovación**, invalida la sesión si transcurrieron 1800 segundos o más. También rechaza sesiones sin reloj. El tiempo lo aporta el servidor, nunca el cliente. La transacción conserva el lock hasta obtener la respuesta, evitando renovaciones concurrentes que se pisen. No se usan vistas streaming ni operaciones largas en esta fase.

Se reconocen estas señales funcionales:

- Navegación GET a panel/admin/concursos con `Sec-Fetch-Mode: navigate` y `Sec-Fetch-User: ?1`, sin indicadores de prefetch. Los navegadores que no envían esos metadatos dependen de las interacciones JS.
- `pointerdown`, `keydown`, `input`, `wheel` y `touchstart` confiables (`isTrusted`) en documento visible. JS envía POST con CSRF, como máximo una vez cada 45 segundos; el servidor admite una renovación cada 30 segundos como mínimo y devuelve 429 antes de ese intervalo. La marca se registra al recibir la señal, sin timers de renovación diferida.

Requests comunes, polling, assets, healthchecks, pestañas ocultas y consultas a `/sesion/estado/` no renuevan. El estado se consulta al abrir/activar la pestaña, al recibir aviso de otra pestaña y al llegar al vencimiento calculado; no hay heartbeat que mantenga viva la sesión. Si hay un error de red, el servidor sigue siendo la autoridad. El reloj técnico de la cookie es de 24 horas para permitir actividad continua; el límite humano sigue siendo siempre de 30 minutos en servidor. `SESSION_SAVE_EVERY_REQUEST=False`.

Las pestañas comparten el reloj PostgreSQL; BroadcastChannel solo sincroniza la UI. El vencimiento se vuelve a comprobar en cada operación aunque el JS falle o esté desactivado. Las señales JS y los metadatos del navegador **no prueban criptográficamente presencia humana**: un cliente construido para falsificarlos puede emitirlas. El throttling puede adelantar el cierre hasta 45 segundos respecto de la última interacción no transmitida; nunca se renueva una sesión ya vencida. Sin JS, los formularios largos pueden vencer mientras se escriben. El mensaje de expiración avisa que los cambios no enviados no se guardaron.

La comprobación de timeout mantiene la semántica de SDD-001: admite o rechaza cada request antes de ejecutar su vista, después de tomar el lock del reloj. Una transacción ya admitida no se cancela por un temporizador durante su procesamiento; esta fase contiene operaciones cortas y no tareas largas. El endpoint de actividad además vuelve a comprobar el plazo antes de renovar.

El login de admin se deriva al login común para inicializar el mismo reloj. El admin conserva sus permisos nativos; una cuenta sin staff recibe acceso restringido. Un cambio de contraseña propio rota la clave nativa de sesión y traslada el reloj sin renovar su fecha. Su adaptación visual usa los tokens compartidos y carga el mismo JS de actividad. No hay usuario ni datos de negocio demo. Ejecutar periódicamente `python manage.py clearsessions` en el contenedor para limpiar sesiones técnicamente caducadas y sus relojes asociados.

## Concursos · SDD-002

Después de actualizar el código, conservar `.env` y el volumen existentes. Estos comandos aplican únicamente las migraciones pendientes y actualizan el servicio local:

```sh
docker compose build web
docker compose run --rm web python manage.py migrate --noinput
docker compose up -d web
docker compose exec web python manage.py test -v 2
```

Acceder a `/concursos/` desde el menú. El superusuario tiene acceso; para otras cuentas, asignar permisos desde `/admin/` → Usuarios → Permisos de usuario (o mediante grupos nativos si el administrador ya los utiliza). No es necesario dar `staff` para operar sobre concursos; `staff` solo habilita el acceso al admin, sujeto a sus permisos.

| Operación | Permisos requeridos |
|---|---|
| Listado y ficha | `concursos.view_concurso` |
| Registrar | Consulta + `concursos.add_concurso` |
| Editar datos | Consulta + `concursos.change_concurso` |
| Cambiar estado o situación | Consulta + `concursos.cambiar_estado_concurso` |

No se asignan permisos automáticamente a cuentas existentes ni se crean roles de negocio. Una cuenta sin autorización recibe acceso restringido y no ve las acciones correspondientes. No hay eliminación de concursos ni edición/eliminación de historial expuestas, tampoco mediante registro de estos modelos en el admin.

Los once datos mínimos son obligatorios: expediente, tipo/modalidad, denominación, funciones, agrupamiento, categoría, tramo, código presupuestario, unidad, dependencia y cadena jerárquica. Los valores se transcriben como texto; no se imponen catálogos, rangos de categoría ni formatos de expediente sin definición aprobada. Se permiten expedientes repetidos. Los datos generales no requieren fojas. Cargo y estructura son datos propios de cada concurso: no se actualizan al editar otro concurso o un catálogo externo.

El alta inicia en **Preparación / Normal** y registra su usuario/fecha. En la ficha se pueden editar los datos generales y, con permiso separado, cambiar manualmente estado principal y/o situación adicional. Todos los estados definidos admiten elección manual; no hay bloqueos por checklist, sugerencias automáticas ni reglas de transición nuevas. La justificación es opcional. Guardar sin diferencias no genera eventos. Cada cambio efectivo conserva anterior/nuevo, autor y fecha, dentro de la misma transacción que actualiza el concurso.

El listado busca por expediente, denominación/funciones y código presupuestario, combina el filtro de estado y pagina de a 20. La ficha muestra todos los datos y pagina el historial de a 20 con sus responsables. Control documental y documentos siguen rotulados como no disponibles, sin enlaces rotos.

Si otro operador guardó una modificación desde que abriste un formulario, tu envío se rechaza con un aviso y conserva tu entrada para revisión. Volvé a abrir la ficha, revisá la modificación reciente y luego realizá el cambio que corresponda. El lock de fila y la versión del registro evitan sobrescribir cambios concurrentes. La edición de datos generales no modifica estados ni genera eventos de estado; sí actualiza responsable/fecha de última modificación. No hay datos de negocio demo ni datos personales reales en las pruebas.

## Interfaz y límites operativos

`static/css/tokens.css` centraliza colores y escalas. `app.css` implementa componentes y responsive; `admin-adapter.css` adapta las variables del admin nativo, cuyo DOM es distinto. El naranja oficial se conserva; para texto pequeño se usa un tono oscuro con mayor contraste. Los botones primarios usan texto grande en negrita. Login tiene layout separado; panel y errores privados comparten navegación, mensajes y componentes. No hay métricas inventadas ni enlaces a módulos pendientes.

Verificar manualmente login, panel, listado, errores, alta/edición, ficha y estados a 360, 768 y 1280 px; recorrer con Tab y revisar foco, etiquetas, tablas y contraste. Las tablas tienen desplazamiento dentro de su región para pantallas angostas. La evidencia efectiva y sus límites se documentan por fase en `docs/SDD-001-EVIDENCIA.md` y `docs/SDD-002-EVIDENCIA.md`.

Compose usa el servidor de desarrollo Django y HTTP local (`DJANGO_DEBUG=True`, cookies Secure desactivadas). No es configuración de producción. Para HTTPS se prevén `DJANGO_HTTPS=True` y `DJANGO_DEBUG=False`; el despliegue, servidor de aplicación, estáticos, proxy y políticas HTTPS pertenecen a una autorización posterior. No fijar cabeceras de proxy confiable sin definir su infraestructura. Cookies de sesión HttpOnly y SameSite=Lax; logout exclusivamente POST/CSRF. No registrar credenciales ni datos personales.

Si Docker informa que no puede conectarse al motor, iniciar Docker Desktop y esperar a que esté listo; en Windows confirmar contenedores Linux/WSL 2. Si el puerto 8000 está ocupado, revisar el proceso antes de cambiar el mapeo. Si faltan tablas, ejecutar `migrate`; si falta un usuario, ejecutar `createsuperuser`. Con `DEBUG=False` el servidor de desarrollo no sirve estáticos: usar el modo local documentado.

## Participantes · SDD-003 (implementación entregada; aceptación pendiente)

Tras aplicar la migración pendiente con `docker compose run --rm web python manage.py migrate --noinput`, los participantes se gestionan desde la ficha de cada concurso. `view_concurso` permite consultar; `add_concurso` junto con consulta permite registrar; `change_concurso` junto con consulta permite corregir datos de participación y de persona. No se necesitan permisos nuevos ni se asignan automáticamente. Todas las rutas de escritura están bajo `/concursos/` y requieren sesión y CSRF.

El DNI se normaliza quitando puntos, guiones y espacios; una persona se reutiliza entre concursos. Al vincular un DNI existente no se cambian silenciosamente sus nombre y apellido: si difieren, el formulario pide revisar la identidad. La corrección explícita de esos datos afecta todos sus vínculos; el cambio de DNI se rechaza si la persona participa en más de un concurso. Los datos de título, cargo y contacto de jurados y veedores pertenecen a cada participación. La representación/calidad de un jurado registrado puede corregirse si la nueva plaza está libre; no se cambia su persona. Los formularios de edición rechazan envíos abiertos antes de otra modificación. No hay eliminación de personas o participantes desde la interfaz, ni reasignación de personas, sustituciones de jurado, checklist automático, designación de ganador o conexión con CoPla. La política definitiva de fotografías históricas de personas sigue pendiente de decisión administrativa.
