# Arranque del proyecto con Codex

Este paquete aporta **instrucciones/especificaciones**, no la aplicación Django. Copiar todos los archivos, incluidas las carpetas ocultas `.agents` y `.codex`, a la **raíz de un repositorio nuevo** llamado `gestion-concursos`.

## Pasos
1. Crear una carpeta/repo vacío `gestion-concursos` (separado de `control-planta`).
2. Descomprimir aquí el contenido del ZIP preservando carpetas ocultas.
3. Abrir la carpeta raíz en VS Code / Codex. Si Codex ya estaba abierto, reiniciar sesión para que detecte las definiciones.
4. Leer `AGENTS.md` y `docs/ROADMAP-SDD.md`.
5. Copiar el texto de `PROMPT-INICIAL-CODEX.md` en Codex.
6. Revisar el resultado **SDD-001** antes de habilitar `SDD-002`.

La carpeta `.codex/agents` contiene subagentes opcionales de revisión y `.agents/skills` contiene skills invocables con `$nombre`. No se instala una dependencia externa por tener estos archivos. La disponibilidad real de subagentes y skills depende de la versión/configuración de Codex; verificarlo antes de atribuirles una revisión.

## Restricciones de la primera entrega
- Sí: Docker + Django + PostgreSQL; login/logout; sesión por inactividad; layout blanco/naranja; panel vacío; pruebas.
- No: concursos, jurados, aspirantes, checklist, DOCX, integración con CoPla.

## Fuentes
Las ordenanzas y los modelos aportados por el usuario están descritos en `docs/FUENTES.md`. **Los PDF originales no están incluidos en este kit**; se deberán incorporar como material de consulta autorizado en la fase que los necesite. Para SDD-001 no son necesarios.
