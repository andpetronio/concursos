---
name: sesion-segura
description: Implementar o auditar el vencimiento Django a los 30 minutos sin actividad real con validación de servidor, sin prolongación por requests automáticas y con logout CSRF.
---
# Sesión por inactividad
Leer `docs/SEGURIDAD.md`. Implementar mecanismo explícito servidor: guardar última actividad reconocida, expirar antes de renovar y no prolongar por healthchecks, assets, polling ni background. No asumir que SESSION_SAVE_EVERY_REQUEST implementa detección humana.
Si se usa endpoint de actividad, autenticar, requerir CSRF y limitar frecuencia; ninguna señal posterior al vencimiento rehabilita sesión. Advertir que una señal JS no prueba criptográficamente una persona presente.
Probar con tiempo controlado: 1799 s, 1800 s, renovación anterior a vencimiento, POST expirado, polling sin renovación, logout POST y sesión multitab. Informar fallos y casos imposibles de verificar.
