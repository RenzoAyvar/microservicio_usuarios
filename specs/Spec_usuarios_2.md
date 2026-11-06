# SPEC-001 v0.2 — Microservicio de Usuarios para una Aplicación de Pagos

## 1. Información general

- **Proyecto:** App Pagos.
- **Módulo:** Microservicio de Usuarios.
- **Versión:** 0.2.
- **Versión anterior:** SPEC-001 v0.1.
- **Tipo de sistema:** Aplicación web con arquitectura basada en microservicios.
- **Actor principal:** Usuario de la aplicación.
- **Actores secundarios:** Microservicios autorizados de la plataforma.
- **Estado:** Especificación actualizada para incorporar integración entre microservicios.

## 2. Objetivo

Desarrollar y mantener un microservicio de usuarios que permita registrar cuentas, iniciar sesión, consultar información personal, actualizar los datos del perfil y proporcionar información básica de los usuarios a otros microservicios autorizados.

El sistema utilizará una aplicación frontend desarrollada con React, un backend en Python con FastAPI y una base de datos MariaDB. Las solicitudes de la aplicación pasarán por un API Gateway que actuará como punto de entrada.

Adicionalmente, el microservicio ofrecerá operaciones internas para que otros servicios de la plataforma puedan consultar información necesaria para sus procesos de negocio, sin acceder directamente a la base de datos de usuarios.

El servicio deberá poder ejecutarse mediante Docker Compose durante el desarrollo y prepararse para su posterior despliegue en Kubernetes, utilizando manifiestos YAML independientes del proveedor de infraestructura.

## 3. Tecnologías

- **Frontend:** React.
- **Backend y API REST:** Python con FastAPI.
- **API Gateway:** Nginx como proxy inverso.
- **Base de datos:** MariaDB 11.8.9.
- **ORM:** SQLAlchemy.
- **Validación de datos:** Pydantic.
- **Autenticación de usuarios:** JWT.
- **Hash de contraseñas:** Argon2id.
- **Documentación:** Swagger UI mediante FastAPI.
- **Pruebas:** Pytest.
- **Contenedores:** Docker y Docker Compose.
- **Orquestación futura:** Kubernetes mediante archivos YAML.
- **Comunicación:** HTTP durante desarrollo; HTTPS en los puntos de entrada de producción que estén expuestos a redes no confiables.

FastAPI generará automáticamente la documentación interactiva de la API, accesible desde `/docs`, y la especificación OpenAPI desde `/openapi.json`.

La implementación deberá mantener separados los mecanismos de autenticación de usuarios y de autenticación entre microservicios.

## 4. Arquitectura del sistema

La aplicación estará compuesta por cuatro capas lógicas:

1. **Cliente APP/Web:** interfaz desarrollada en React.
2. **API Gateway:** Nginx recibirá las solicitudes y las dirigirá al backend.
3. **Microservicio de Usuarios:** FastAPI implementará la lógica de negocio y las operaciones de integración.
4. **Base de datos:** MariaDB almacenará los usuarios y sus roles.

Flujo de la aplicación:

`React → Nginx API Gateway → FastAPI → MariaDB`

Flujo de integración entre microservicios:

`Microservicio consumidor → Red interna → Microservicio de Usuarios → MariaDB`

Las respuestas regresarán por el recorrido correspondiente.

El API Gateway realizará el enrutamiento de las solicitudes de la aplicación. El microservicio de usuarios validará los datos, verificará las credenciales y ejecutará las operaciones.

Las integraciones internas no deberán acceder directamente a MariaDB ni depender de direcciones IP fijas.

## 5. Funcionalidades requeridas

### RF-01. Registrar usuario

El sistema permitirá crear una cuenta mediante un formulario de registro.

Datos obligatorios:

- Nombre.
- Apellido.
- Correo electrónico.
- Contraseña.
- Fecha de nacimiento.
- Teléfono.

Datos opcionales:

- Dirección.

Reglas:

- El correo debe tener un formato válido y no estar registrado.
- El correo se normalizará para evitar registros duplicados por diferencias entre mayúsculas y minúsculas.
- La contraseña debe tener un mínimo de 8 y un máximo de 16 caracteres.
- La contraseña debe contener al menos una letra mayúscula, una letra minúscula y un número.
- La contraseña debe almacenarse mediante un hash Argon2id, nunca en texto plano.
- El nuevo usuario tendrá el estado activo y el rol predeterminado de usuario común.
- El cliente no podrá asignarse el rol de administrador durante el registro público.
- El sistema registrará la fecha de creación.

Resultado esperado: se crea la cuenta y se devuelve una respuesta de confirmación sin exponer la contraseña ni su hash.

### RF-02. Iniciar sesión

El sistema permitirá iniciar sesión mediante correo electrónico y contraseña.

Reglas:

- Se comprobarán las credenciales.
- Las cuentas inactivas no podrán iniciar sesión.
- Si las credenciales son correctas, se emitirá un JWT con tiempo de expiración de 3 horas.
- El sistema actualizará la fecha del último acceso.
- Si las credenciales son incorrectas, se devolverá un mensaje genérico: "Credenciales incorrectas".
- Luego de tres intentos fallidos, la cuenta bloqueará nuevos intentos de acceso durante 15 minutos.

El JWT será validado por el backend en las operaciones protegidas.

No se almacenarán tokens de acceso en una tabla MariaDB en esta versión.

Los intentos fallidos deberán gestionarse de manera consistente con el número de réplicas del backend. Si se utilizan varias réplicas, el mecanismo de bloqueo no podrá depender exclusivamente de la memoria local de cada proceso.

### RF-03. Consultar usuario autenticado

El sistema permitirá consultar la información del usuario autenticado.

Endpoint:

`GET /api/users/me`

Datos que se podrán mostrar:

- Identificador.
- Nombre y apellido.
- Correo electrónico.
- Estado de la cuenta.
- Fecha de registro.
- Último acceso.
- Rol.
- Teléfono.
- Dirección.
- Fecha de nacimiento.

Reglas:

- Será obligatorio presentar un JWT válido.
- La contraseña y el hash nunca aparecerán en la respuesta.
- En esta operación, el usuario solo podrá consultar su propia información.
- Un usuario no podrá consultar los datos de otra cuenta mediante el cambio de un identificador.
- El usuario deberá estar activo para acceder a su perfil.

### RF-04. Actualizar datos

El sistema permitirá actualizar los datos personales y del perfil del usuario autenticado.

Endpoint:

`PUT /api/users/me`

Campos modificables:

- Nombre.
- Apellido.
- Correo electrónico.
- Teléfono.
- Dirección.
- Fecha de nacimiento.

Reglas:

- Se requerirá un JWT válido.
- Los campos deberán superar las validaciones correspondientes.
- El correo deberá seguir siendo único.
- No se permitirá modificar el identificador, el rol, el estado de la cuenta ni el hash de la contraseña mediante este endpoint.
- La fecha de actualización se modificará cuando corresponda.
- El usuario solo podrá modificar su propio perfil.

El cambio de contraseña podrá añadirse como una funcionalidad independiente en una versión posterior.

### RF-05. Consultar usuario mediante identificador para integración interna

El sistema permitirá que microservicios autorizados consulten la existencia y el estado de un usuario mediante su identificador `id_usuario`.

Endpoint propuesto:

`GET /internal/users/{id_usuario}`

Ejemplo:

```http
GET /internal/users/15
```

Respuesta cuando el usuario existe y está activo:

```json
{
  "id_usuario": 15,
  "estado": true
}
```

Respuesta cuando el usuario existe, pero está inactivo:

```json
{
  "id_usuario": 15,
  "estado": false
}
```

Reglas:

- El identificador debe ser un entero válido.
- Solo los microservicios autenticados y autorizados podrán consumir esta operación.
- No se exigirá el JWT personal de un usuario de la aplicación.
- La respuesta contendrá únicamente la información necesaria para validar la existencia y el estado del usuario.
- No se devolverán contraseñas, hashes, correos, teléfonos, direcciones ni otros datos personales.
- La consulta no modificará información del usuario.
- La operación no deberá permitir consultar información arbitraria de la base de datos.

Respuestas:

| Código | Condición |
|---|---|
| 200 OK | Usuario encontrado, activo o inactivo |
| 401 Unauthorized | Consumidor sin credenciales válidas |
| 403 Forbidden | Consumidor autenticado sin permisos |
| 404 Not Found | Usuario inexistente |
| 422 Unprocessable Entity | Identificador inválido |
| 500 Internal Server Error | Error inesperado |

La respuesta `200 OK` con `estado: false` permitirá distinguir un usuario existente pero inactivo de uno que no existe.

### RF-06. Autenticar microservicios consumidores

El sistema contará con API Keys independientes para autenticar las solicitudes realizadas por otros microservicios.

Este mecanismo será distinto del JWT utilizado por los usuarios de la aplicación. El JWT personal nunca se utilizará para comunicación entre microservicios.

Decisión técnica aprobada:

- Cada microservicio consumidor tendrá una API Key única.
- La API Key se enviará mediante la cabecera HTTP `X-API-Key`.
- El microservicio de usuarios identificará al consumidor a partir de la API Key.
- El microservicio validará que el consumidor autenticado tenga los permisos necesarios antes de ejecutar una operación interna.
- Para `GET /internal/users/{id_usuario}`, se utilizará inicialmente el permiso `users:read_status`.
- Las API Keys se configurarán mediante variables de entorno en desarrollo y Kubernetes Secrets en Kubernetes.
- Las API Keys deberán permitir rotación sin afectar la disponibilidad inmediata.

#### Identificación y permisos

Cada consumidor tendrá un identificador estable definido en la configuración, por ejemplo `pagos-service` o `notificaciones-service`. La configuración del microservicio de usuarios deberá asociar cada consumidor con sus permisos:

```text
Consumer ID: pagos-service
Permisos: users:read_status

Consumer ID: otro-servicio
Permisos: otro-permiso-futuro
```

La asociación conceptual será una tabla de configuración externa, administrada fuera del código fuente, con esta información:

```text
identificador del consumidor
huella digital de la API Key actual
huellas digitales opcionales de API Keys anteriores durante la rotación
lista de permisos
estado habilitado o deshabilitado
```

La API Key real no se almacenará ni se transmitirá como parte de esta tabla. En el microservicio de usuarios se almacenará únicamente una huella criptográfica derivada con SHA-256 o un algoritmo equivalente, la cual permitirá buscar el consumidor sin guardar la clave en texto plano. Las API Keys deberán generarse con suficiente aleatoriedad, por ejemplo con al menos 256 bits de entropía. Si se exige protección adicional frente a uso fuera de la plataforma, la huella podrá calcularse también con una clave HMAC mantenida como secreto.

El flujo de una solicitud interna será:

1. Obtener la cabecera `X-API-Key`.
2. Buscar la huella de la clave mediante una comparación segura contra las claves activas configuradas.
3. Obtener el consumidor asociado y verificar que esté habilitado.
4. Verificar que el consumidor tenga el permiso exigido por el endpoint.
5. Ejecutar la operación solo si ambas validaciones son exitosas.

Una API Key ausente, inválida o deshabilitada producirá `401 Unauthorized`. Una API Key válida sin el permiso requerido producirá `403 Forbidden`. No se expondrá cuál consumidor o clave fue reconocido en las respuestas de error.

#### Configuración en Docker Compose

En desarrollo, cada microservicio consumidor configurará su propia clave mediante una variable de entorno. El consumidor enviará esa clave en `X-API-Key`.

Ejemplo conceptual de configuración del consumidor:

```text
USERS_SERVICE_API_KEY=${PAGOS_USERS_SERVICE_API_KEY}
```

En Docker Compose, las variables se proporcionarán por un archivo de entorno local o por variables externas, nunca con el valor real de la clave dentro de archivos versionados:

```yaml
environment:
  USERS_SERVICE_API_KEY: ${PAGOS_USERS_SERVICE_API_KEY}
```

El microservicio de usuarios recibirá la configuración de identificación y permisos mediante variables externas o archivos locales excluidos de Git. La versión inicial podrá utilizar una variable estructurada, por ejemplo:

```text
INTERNAL_SERVICE_CREDENTIALS=<configuración JSON de consumidores, huellas digitales y permisos>
```

La implementación deberá validar la estructura de esta configuración al iniciar el proceso. Una configuración duplicada, una huella vacía o permisos desconocidos causará un error explícito de configuración.

#### Configuración en Kubernetes

Cada microservicio consumidor tendrá su API Key en un Kubernetes Secret independiente o en una entrada separada dentro de un Secret autorizado. El contenedor consumidor la recibirá mediante `secretKeyRef`.

El microservicio de usuarios recibirá las huellas digitales de claves, identificadores y permisos mediante Kubernetes Secrets o mediante la combinación de ConfigMap para metadatos no sensibles y Secret para las huellas. Los secrets se definirán fuera del manifiesto que contenga el código o un valor real.

La comunicación se realizará dentro de la red interna mediante Service de tipo ClusterIP. El endpoint `/internal` no se incluirá en las rutas públicas de Nginx ni se expondrá mediante un recurso público de entrada.

#### Rotación segura

La API Key deberá poder rotarse sin interrumpir a los consumidores. El procedimiento será:

1. Generar una clave nueva con alta entropía.
2. Registrar temporalmente la nueva huella como clave actual y conservar la huella anterior como clave aceptada de respaldo.
3. Distribuir la clave nueva al consumidor mediante su Secret o variable de entorno y reiniciar o actualizar únicamente los pods necesarios.
4. Confirmar que el consumidor usa la nueva clave mediante observabilidad segura.
5. Eliminar la huella anterior una vez finalizado el período de convivencia.

Durante la coexistencia, el microservicio de usuarios podrá aceptar ambas huellas y ambas deberán resolver al mismo identificador y permisos. Las fechas de activación y expiración de cada clave deberán mantenerse en la configuración de despliegue y serán validadas al iniciar o recargar la configuración.

La comparación de API Keys deberá ejecutarse con comparación constante para no depender del tiempo de comparación. Los valores de configuración no deberán aparecer en logs, trazas, métricas o respuestas HTTP. En caso de una clave comprometida, la huella correspondiente se eliminará o deshabilitará de forma inmediata, y se rotarán las credenciales necesarias.

#### Evolución futura

JWT independiente para servicios consumidores, autenticación mutua mediante certificados TLS (mTLS) y OAuth 2.0 Client Credentials son posibles evoluciones futuras. Se podrán incorporar cuando la plataforma requiera emisión centralizada, identidad criptográfica adicional o políticas de seguridad más avanzadas. Esta versión no implementará ninguno de estos mecanismos ni un servidor de identidad centralizado.

Reglas:

- Cada microservicio consumidor deberá poder identificarse.
- Las solicitudes internas deberán autenticarse antes de acceder a operaciones protegidas.
- El sistema deberá distinguir entre autenticación y autorización.
- Un microservicio autenticado solo podrá ejecutar las operaciones para las que tenga permisos.
- Las credenciales no se almacenarán directamente en el código fuente.
- Las credenciales deberán gestionarse mediante configuración externa y Kubernetes Secrets durante el despliegue.
- El mecanismo deberá permitir rotación de credenciales.

### RF-07. Comprobar disponibilidad

El sistema permitirá comprobar la disponibilidad del microservicio.

Endpoint:

`GET /api/health`

Respuesta:

```json
{
  "status": "ok"
}
```

Esta operación permitirá comprobar que el proceso FastAPI está operativo.

La comprobación de disponibilidad de MariaDB podrá implementarse mediante una verificación independiente, sin confundir la salud del proceso con la disponibilidad de sus dependencias.

## 6. Modelo de datos

La base de datos MariaDB se llamará `app_pagos_usuarios`.

### Tabla `rol`

- `id_rol`: INT, PK, autoincremental.
- `nombre`: VARCHAR(50), único, no nulo.
- `descripcion`: VARCHAR(50), opcional.

Roles iniciales:

- `usuario`
- `administrador`

### Tabla `usuario`

- `id_usuario`: INT, PK, autoincremental.
- `nombre`: VARCHAR(100), no nulo.
- `apellido`: VARCHAR(100), no nulo.
- `email`: VARCHAR(150), no nulo, único.
- `password_hash`: VARCHAR(255), no nulo.
- `estado`: BOOLEAN, no nulo, predeterminado verdadero.
- `fecha_registro`: DATETIME, no nulo.
- `fecha_actualizacion`: DATETIME, opcional.
- `ultimo_acceso`: DATETIME, opcional.
- `id_rol`: INT, FK a `rol.id_rol`, no nulo.
- `telefono`: VARCHAR(20), no nulo.
- `direccion`: VARCHAR(150), opcional.
- `fecha_nacimiento`: DATE, no nulo.

Relación: un rol puede estar asociado a muchos usuarios; cada usuario tendrá un único rol.

Las tablas `perfil_usuario`, `usuario_rol`, `token` y `login_intento` no se crearán en esta versión, salvo que una modificación futura del diseño sea aprobada expresamente.

La nueva operación interna de consulta no deberá requerir cambios en el modelo de datos.

## 7. API REST

Todos los endpoints de la aplicación se expondrán mediante el prefijo `/api`.

| Método | Endpoint | Propósito | Acceso |
|---|---|---|---|
| POST | `/api/auth/register` | Registrar usuario | Público |
| POST | `/api/auth/login` | Iniciar sesión | Público |
| GET | `/api/users/me` | Consultar perfil propio | JWT de usuario |
| PUT | `/api/users/me` | Actualizar perfil propio | JWT de usuario |
| GET | `/api/health` | Comprobar disponibilidad | Público |

Las operaciones internas se separarán del prefijo público:

| Método | Endpoint | Propósito | Acceso |
|---|---|---|---|
| GET | `/internal/users/{id_usuario}` | Consultar existencia y estado del usuario | Microservicio autorizado |

El endpoint interno no deberá exponerse a través de la ruta pública del API Gateway.

La separación deberá aplicarse tanto en Nginx como en la configuración de red y los permisos del entorno de despliegue.

### Respuestas esperadas

- `200 OK`: operación realizada correctamente.
- `201 Created`: usuario registrado.
- `400 Bad Request`: solicitud inválida o conflicto de negocio según el endpoint.
- `401 Unauthorized`: credenciales ausentes, inválidas o token de usuario inválido.
- `403 Forbidden`: operación no permitida o consumidor sin autorización.
- `404 Not Found`: usuario o recurso inexistente.
- `409 Conflict`: correo ya registrado.
- `422 Unprocessable Entity`: errores de validación de entrada.
- `500 Internal Server Error`: error inesperado.

Las respuestas de error deberán ser consistentes y no exponer consultas SQL, contraseñas, tokens ni trazas internas.

## 8. Requisitos de seguridad

- Todas las contraseñas se almacenarán como hashes Argon2id.
- Los endpoints protegidos por autenticación de usuario exigirán un JWT firmado y no expirado.
- La clave de firma JWT se obtendrá de una variable de entorno.
- La clave JWT real no se incluirá en el repositorio.
- El JWT tendrá una duración limitada de tres horas, definida mediante configuración.
- Las solicitudes internas deberán contar con autenticación y autorización independientes de la sesión del usuario.
- Las consultas a MariaDB utilizarán SQLAlchemy y mecanismos seguros de parametrización.
- Los datos de entrada se validarán mediante Pydantic.
- Se habilitará CORS únicamente para los orígenes autorizados que necesiten acceder desde el navegador.
- En los puntos de entrada de producción expuestos a redes no confiables se utilizará HTTPS.
- La API interna no tendrá exposición pública directa.
- Se limitarán las solicitudes de autenticación mediante el gateway o controles equivalentes.
- No se devolverá `password_hash` en ninguna respuesta.
- Las API Keys internas se leerán desde variables de entorno o Kubernetes Secrets y nunca se incluirán en el código fuente o imágenes de contenedor.
- Las API Keys internas no deberán aparecer en logs, respuestas HTTP, métricas ni trazas.
- La validación interna usará comparación segura de huellas criptográficas y distinguirá autenticación de autorización.
- La cabecera `X-API-Key` se utilizará exclusivamente para autenticar consumidores internos.
- El JWT personal de usuarios no será aceptado como credencial de microservicio.
- Los datos personales solo podrán ser consultados o modificados por el propietario de la cuenta, salvo operaciones expresamente autorizadas.
- MariaDB no tendrá acceso público.
- Los secretos de despliegue se administrarán fuera del código fuente.

## 9. Requisitos no funcionales

- **Mantenibilidad:** separar rutas, modelos, esquemas, servicios y configuración.
- **Compatibilidad:** frontend y backend intercambiarán JSON mediante HTTP.
- **Integridad:** MariaDB aplicará claves primarias, foráneas y restricciones de unicidad.
- **Usabilidad:** los formularios mostrarán errores comprensibles.
- **Pruebas:** las operaciones principales tendrán pruebas automatizadas.
- **Configuración:** las credenciales de MariaDB, la clave JWT y los orígenes CORS se gestionarán mediante variables de entorno.
- **Interoperabilidad:** los microservicios utilizarán contratos de API documentados y respuestas consistentes.
- **Desacoplamiento:** ningún microservicio consumidor accederá directamente a la base de datos de usuarios.
- **Portabilidad:** el proyecto podrá desplegarse en distintos entornos Kubernetes sin depender obligatoriamente de AWS.
- **Escalabilidad:** la aplicación deberá poder ejecutarse con varias réplicas, siempre que el estado compartido necesario para la lógica de negocio no dependa exclusivamente de la memoria local.
- **Observabilidad:** el servicio deberá ofrecer una operación de salud y generar registros que faciliten el diagnóstico de errores.

## 10. Compatibilidad con Docker y Kubernetes

El proyecto conservará Docker Compose como mecanismo de ejecución local y pruebas de integración.

Se preparará para un despliegue futuro en Kubernetes mediante manifiestos YAML.

La infraestructura deberá contemplar:

- Namespace independiente para el microservicio.
- Deployment para FastAPI.
- Service interno de tipo ClusterIP para FastAPI.
- StatefulSet para MariaDB.
- Persistencia mediante PersistentVolumeClaim.
- Service interno para MariaDB.
- Deployment para Nginx.
- ConfigMap para configuraciones no sensibles.
- Secret para credenciales y claves.
- Readiness y liveness probes.
- Configuración de recursos y réplicas.
- Políticas de red para restringir las comunicaciones cuando el entorno las soporte.

La configuración no deberá depender de IP fijas, nombres de recursos propios de AWS ni características exclusivas de un proveedor.

El mecanismo de acceso externo, cuando sea necesario para la aplicación, se definirá de forma independiente de la comunicación interna entre microservicios.

La operación `/internal/users/{id_usuario}` deberá estar disponible únicamente dentro de la red autorizada.

## 11. Fuera del alcance de esta versión

- Gestión de pagos y transferencias.
- Recuperación de contraseña por correo.
- Verificación de correo electrónico.
- Autenticación de dos factores.
- Administración avanzada de roles y permisos.
- Almacenamiento de sesiones o tokens de usuario en una tabla.
- Gestión de billeteras, depósitos y retiros.
- Acceso directo de otros microservicios a MariaDB.
- Despliegue definitivo en una plataforma Kubernetes específica.
- Implementación de un sistema centralizado de identidad para toda la plataforma.

La autenticación entre microservicios y la consulta interna sí forman parte del alcance de la versión 0.2; su mecanismo concreto de autenticación deberá definirse antes de su implementación.

## 12. Criterios de aceptación

1. Un visitante puede registrar una cuenta con datos válidos.
2. El sistema rechaza correos duplicados.
3. Las contraseñas no se almacenan en texto plano.
4. Un usuario registrado puede iniciar sesión con sus credenciales correctas.
5. Un inicio de sesión incorrecto no devuelve un JWT válido.
6. Las cuentas inactivas no pueden iniciar sesión.
7. Un usuario autenticado puede consultar sus propios datos.
8. Un usuario autenticado puede actualizar los datos permitidos.
9. Las solicitudes protegidas sin JWT válido son rechazadas.
10. Ninguna respuesta expone el hash de la contraseña.
11. El frontend consume el backend mediante el API Gateway.
12. Los datos persisten en MariaDB después de reiniciar el backend.
13. Los endpoints principales pueden probarse mediante Swagger UI y pruebas automatizadas.
14. Un microservicio autenticado y autorizado puede consultar un usuario mediante `id_usuario`.
15. La consulta interna devuelve `200 OK` y `estado: true` cuando el usuario existe y está activo.
16. La consulta interna devuelve `200 OK` y `estado: false` cuando el usuario existe y está inactivo.
17. La consulta interna devuelve `404 Not Found` cuando el usuario no existe.
18. Un consumidor sin credenciales válidas no puede acceder a la operación interna.
19. Un consumidor autenticado sin permisos no puede ejecutar operaciones no autorizadas.
20. La operación interna no devuelve información personal innecesaria.
21. El endpoint interno no está expuesto mediante el acceso público del API Gateway.
22. La configuración sensible no está almacenada en el repositorio.
23. La aplicación puede ejecutarse mediante Docker Compose sin perder sus funcionalidades actuales.

## 13. Orden sugerido de implementación

1. Revisar el código actual y compararlo con SPEC-001 v0.2.
2. Identificar las diferencias entre la implementación y los nuevos requisitos.
3. Presentar una propuesta de autenticación entre microservicios.
4. Aprobar el mecanismo de autenticación y autorización interna.
5. Implementar `GET /internal/users/{id_usuario}`.
6. Implementar la autenticación y autorización de los consumidores.
7. Mantener las operaciones existentes de registro, login, consulta y actualización de perfil.
8. Actualizar la documentación Swagger/OpenAPI.
9. Actualizar el contrato de integración para otros microservicios.
10. Crear y ejecutar pruebas automatizadas de las operaciones nuevas y existentes.
11. Verificar el funcionamiento completo mediante Docker Compose.
12. Preparar los manifiestos Kubernetes YAML.
13. Desplegar y verificar el microservicio en un entorno Kubernetes.

## 14. Entregables

- Código actualizado del microservicio de usuarios.
- SPEC-001 v0.2 actualizado.
- Endpoint interno de consulta de usuarios.
- Mecanismo de autenticación y autorización entre microservicios.
- Pruebas automatizadas.
- Documentación Swagger/OpenAPI.
- Contrato de integración para los equipos consumidores.
- Docker Compose actualizado.
- Manifiestos Kubernetes YAML.
- Guía de despliegue y configuración.

**Resultado final esperado:** un microservicio de usuarios funcional, seguro y preparado para integrarse con otros microservicios de App Pagos. Deberá conservar el registro, autenticación y administración de perfiles, y ofrecer una operación interna que permita validar la existencia y el estado de los usuarios sin exponer datos personales ni acceder directamente a su base de datos.