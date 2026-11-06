# Revisión y correcciones del microservicio de usuarios antes del despliegue en Kubernetes

Analiza el estado actual del repositorio `RenzoAyvar/microservicio_usuarios`. No reconstruyas el proyecto desde cero ni elimines funcionalidades existentes.

## 1. Configuración de producción
- Eliminar SQLite como fallback silencioso para producción.
- Mantener la posibilidad de ejecutar el proyecto localmente con MariaDB.
- Leer `DATABASE_URL` desde variables de entorno.
- Validar que las variables críticas estén configuradas al iniciar.
- No incluir credenciales reales en el repositorio.

## 2. Autenticación entre microservicios
Implementar autenticación mediante API Keys individuales.

Requisitos:
- Cada consumidor tendrá su propia API Key.
- El backend almacenará y comparará hashes SHA-256, nunca las claves originales.
- Leer `INTERNAL_SERVICE_CREDENTIALS` desde variables de entorno.
- Verificar que el consumidor esté habilitado.
- Verificar los permisos asignados.
- Implementar el permiso `users:read_status`.

## 3. Endpoint interno
Implementar:

`GET /internal/users/{id_usuario}`

Debe:
- Exigir API Key válida.
- Exigir el permiso `users:read_status`.
- Consultar al usuario en MariaDB.
- Devolver únicamente `id_usuario` y `estado`.
- Responder 404 si no existe el usuario.
- No exponer información personal.

## 4. Protección del API Gateway
Modificar Nginx para que:
- Exponga los endpoints públicos del microservicio.
- No permita acceder externamente a `/internal/`.
- Mantenga la comunicación interna entre servicios dentro del clúster.

## 5. Preparación para Kubernetes
- Mantener la aplicación compatible con Docker.
- No depender de `localhost` para conectarse a MariaDB en Kubernetes.
- Permitir configurar la conexión mediante el DNS del Service.
- Utilizar variables de entorno para los secretos.
- Incorporar un endpoint de readiness y otro de liveness apropiados.
- Evitar que el backend dependa de archivos `.env` dentro de la imagen.

## 6. Pruebas
Agregar pruebas para:
- API Key válida.
- API Key inválida.
- Consumidor deshabilitado.
- Permiso insuficiente.
- Usuario existente.
- Usuario inexistente.
- Respuesta sin datos personales.
- Acceso externo bloqueado al endpoint interno.

## 7. Entregables
- Código actualizado.
- Pruebas automatizadas.
- Actualización de README.
- Actualización de especificaciones.
- Lista de variables de entorno necesarias.
- Confirmación de que el proyecto sigue funcionando con Docker Compose.

No crear todavía manifiestos Kubernetes ni modificar recursos AWS. Primero completar y verificar la aplicación.

## Estado de implementación

El backend incorpora validación de variables críticas, autenticación interna por
API Keys individuales, readiness/liveness separados y bloqueo de `/internal/`
en los gateways Nginx. Las API Keys deben suministrarse como huellas SHA-256.