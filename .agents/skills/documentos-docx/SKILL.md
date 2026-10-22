---
name: documentos-docx
description: Crear y validar proyectos de resoluciones, oficios, notas y actas de concursos en DOCX editables, diferenciando proyecto, documento oficial y requisito documental.
---
# Generación documental (solo cuando se habilite SDD-005)
1. Leer `docs/specs/005-generacion-docx.md`, `docs/FUENTES.md` y modelos PDF originales disponibles.
2. No confundir PDF aportado con DOCX editable; reconstruir la plantilla con revisión humana de formato y texto.
3. Usar datos ya registrados del concurso, jurados, aspirantes y fojas; registrar campos críticos faltantes y bloquear salida incompleta.
4. Generar DOCX editable y verificar su estructura, tablas, saltos y ausencia de placeholders no resueltos, con datos ficticios.
5. Nunca dar por emitida/firmada/publicada una resolución por generar su proyecto. Evitar almacenar PII innecesaria en logs.
6. Conservar versionado de plantillas y trazabilidad del documento generado.
