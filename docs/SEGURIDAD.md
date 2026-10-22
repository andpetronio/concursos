# Política de seguridad para la primera versión

## Sesión: 30 minutos de inactividad real
La sesión autenticada **vence en servidor** a los **1.800 segundos** desde la última actividad intencional reconocida. No basta con un temporizador visual ni con `SESSION_COOKIE_AGE` por sí solo.

Requisitos de comportamiento:
1. En login exitoso queda inicializada la fecha de última actividad reconocida.
2. En cada request protegido, el servidor comprueba la fecha **antes** de ejecutar la vista o admitir una renovación. Si el plazo venció, invalida la sesión y exige login.
3. Solo acciones iniciadas por el usuario (navegación, envíos, interacciones de interfaz registradas de manera acotada) renuevan el plazo. **No** hacerlo con polling, precarga, healthchecks, assets ni solicitudes automáticas. No usar `SESSION_SAVE_EVERY_REQUEST=True` como solución indiscriminada.
4. Si se registra actividad JS, el endpoint debe ser autenticado, CSRF-protegido, limitado en frecuencia y nunca debe renovar una sesión **ya vencida**. La actividad del cliente es una señal funcional, no una prueba criptográfica de presencia humana; los endpoints críticos vuelven a validar el estado en servidor.
5. Varias pestañas comparten sesión; ninguna pestaña inactiva debe renovar por sí sola. Tras vencer, los POST protegidos nunca modifican datos.
6. Logout por POST + CSRF y caducidad del servidor, no solo redirección de frontend.
7. Si expira mientras el usuario completa un formulario, no se guarda sin autenticación. Avisar sin exponer datos ni generar cambios parciales.

**Criterio mínimo de prueba**: congelar/simular tiempo; 1799 s + actividad válida renueva; 1800 s sin actividad expira; requests automáticos no renuevan; login/logout; sesión expirada bloquea GET y POST protegidos; pestañas múltiples; cookies y CSRF correctos.

## Django seguro
- `DEBUG` vía entorno, `SECRET_KEY` desde variables; nunca exponer claves.
- Cookies `HttpOnly`, `SameSite` y `Secure` en HTTPS de producción; documentación clara de diferencias local/producción.
- Autenticación/CSRF native Django, permisos de escritura y gestión de errores sin rastros internos para usuarios.
- Guardar solo datos imprescindibles; DNI y contactos son datos personales. No loguearlos, volcarlos en errores ni usarlos como claves técnicas visibles por defecto.
- Evitar dependencias extra sin justificación; usar versiones compatibles y fijadas reproduciblemente.
