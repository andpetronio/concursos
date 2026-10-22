---
name: django-calidad
description: Diseñar, implementar o revisar backend Django, migraciones PostgreSQL, formularios, permisos y pruebas evitando duplicación de lógica y sobreingeniería.
---
# Calidad idiomática Django
- Usar ORM, ModelForms/Forms, auth, sesiones, permisos, URL dispatcher, mensajes y CSRF antes de inventar capas.
- Ubicar invariantes en modelos/servicios donde correspondan; validación de formularios para entrada de usuario; evitar signals opacos.
- Migraciones normales y reversibles cuando se pueda, sin borrar datos; uso explícito de transacciones en operaciones multientidad.
- Tests de comportamiento y límites, no solo tests que comprueban implementación interna; sin datos personales reales.
- Usar una convención coherente de nombres, layout y pruebas. Priorizar legibilidad, mantenibilidad y eficiencia razonable.
- Antes del cierre: `manage.py check`, `makemigrations --check --dry-run` cuando existan modelos y suite adecuada; reportar comandos reales y defectos no resueltos.
