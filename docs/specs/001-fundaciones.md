# SDD-001 — Fundaciones del Sistema de Concursos

**Estado:** AUTORIZADA. **Única especificación a implementar en el primer pedido.**

## Objetivo
Proyecto Django/PostgreSQL usable en entorno local con Docker Compose, inicio/cierre de sesión, vencimiento por 30 minutos de inactividad real del usuario, UI institucional blanco/naranja y panel inicial mínimo.

## Entregables
1. Código y configuración mínima de Django con DB PostgreSQL, Compose con `web`/`db` y volumen persistente. `.env.example` documentado, `.env` ignorado.
2. Login seguro como vista separada, sin sidebar del área privada. Panel autenticado y logout POST protegido por CSRF. Auth/admin nativo para crear usuario inicial; nada de gestor visual de usuarios todavía.
3. Sesión vencida a los 1800 segundos de inactividad **verificada en servidor**; no renovación por polling, pestañas inactivas, assets o healthchecks. Detallar explícitamente qué señales se consideran actividad y cómo se comprueban, según `docs/SEGURIDAD.md`.
4. Sistema de diseño: tokens CSS centralizados; layouts compartidos; componentes base reutilizables (botón, formulario, mensaje, tarjeta, cabecera, navegación); responsive y accesibilidad básica.
5. Dashboard mínimo sin métricas inventadas ni enlaces a módulos inexistentes.
6. Tests automatizados y README con preparación/arranque, migraciones, creación de usuario y pruebas, usando macOS y PowerShell/Windows 11 con Docker Desktop.

## Pruebas obligatorias
- Login válido/inválido; ruta protegida deniega anónimo; logout POST termina sesión y GET no la destruye.
- Exactamente antes/después del límite de 1800 segundos; sesión vencida bloquea lectura y POST protegido; una acción real anterior al límite renueva sin aceptar renovación de sesión ya vencida.
- Requests automáticas/background no prolongan sesión; simulación de pestañas múltiples coherente.
- `manage.py check`, migraciones reproducibles y suite de tests dentro del contenedor.
- UI: login sin menú privado, tokens aplicados en dashboard; errores, foco y dimensiones comunes revisados, con evidencia o límite declarado.

## Definition of Done
Checklist `docs/QA.md` completo; revisiones independientes (Django, UI, seguridad) si están disponibles; defectos críticos corregidos; guía para levantar ambiente. No afirmar pruebas que no se ejecutaron.

## No objetivos
Sin concursos, jurados, veedores, aspirantes, fojas, checklist, DOCX, APIs, mensajería, roles complejos, integración CoPla, producción/cloud ni datos de negocio demo.

## Salida solicitada
Lista de archivos, decisiones mínimas, comandos/casos probados con resultado real, instrucciones de inicio, riesgos pendientes. **Detenerse y esperar autorización para SDD-002.**
