# Microservicio de Usuarios — Datos para integración entre microservicios

Este documento contiene la información necesaria para que otros equipos puedan consumir el microservicio de usuarios de App Pagos.

El microservicio administra el registro, autenticación y consulta de perfiles de los usuarios. Otros microservicios podrán necesitar consultar información del usuario para validar su existencia y estado antes de realizar operaciones de negocio.

**Estado del contrato:** versión inicial basada en la implementación actual del repositorio.

## 1. Dirección

| Dato | Valor |
|---|---|
| Servicio | Microservicio de Usuarios |
| Tecnología | Python + FastAPI |
| Base de datos | MariaDB 11.8.9 |
| API Gateway | Nginx |
| Puerto interno FastAPI | 8000 |
| Protocolo actual | HTTP |
| Acceso previsto | Interno |
| Base URL interna | `http://users-api.app-pagos.svc.cluster.local:8000` |
| Salud | `GET /api/health` |
| Documentación | `/docs` |
| Especificación OpenAPI | `/openapi.json` |

En Kubernetes, los microservicios consumidores utilizarán el DNS completo del
Service `users-api` en el namespace `app-pagos`. La comunicación es interna al
clúster; no se debe utilizar una IP fija ni una dirección pública.

## 2. Autenticación

### 2.1. Autenticación de usuarios

El inicio de sesión utiliza correo electrónico y contraseña.

Cuando las credenciales son válidas, el servicio devuelve un JWT.

| Dato | Valor |
|---|---|
| Tipo | Bearer Token |
| Algoritmo | HS256 |
| Emisor (`iss`) | No configurado actualmente |
| Sujeto (`sub`) | Correo electrónico del usuario |
| Expiración | 3 horas |
| Clave de firma | Variable de entorno `JWT_SECRET_KEY` |

Encabezado para operaciones protegidas:

```http
Authorization: Bearer <jwt>
```

El token se utiliza actualmente para identificar al usuario autenticado y permitirle consultar o actualizar su propio perfil.

### 2.2. Autenticación entre microservicios

Las solicitudes de servicio a servicio usan una API Key propia de cada consumidor.

La API Key se transmite mediante:

```http
X-API-Key: <api-key>
```

El backend almacena únicamente huellas SHA-256 de las claves configuradas en
`INTERNAL_SERVICE_CREDENTIALS` y compara las huellas en tiempo constante.
Cada consumidor debe declarar:

- `key_hashes`: una o varias huellas SHA-256.
- `permissions`: permisos habilitados.
- `enabled`: si el consumidor puede autenticarse.

El permiso requerido por el endpoint interno es `users:read_status`. Las API
Keys y el JWT tienen responsabilidades independientes; una API Key no sustituye
un JWT de usuario.

## 3. Endpoints disponibles

Los siguientes endpoints corresponden a la implementación actual.

### 3.1. Registrar usuario

```http
POST /api/auth/register
Content-Type: application/json
```

Permite registrar una cuenta nueva.

Solicitud:

```json
{
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan@example.com",
  "password": "Clave1234",
  "telefono": "987654321",
  "direccion": "Av. Principal 123",
  "fecha_nacimiento": "2000-05-15"
}
```

Reglas:

- El correo debe tener un formato válido.
- El correo se normaliza a minúsculas.
- No se permiten correos duplicados.
- La contraseña debe tener entre 8 y 16 caracteres, una mayúscula, una minúscula y un número.
- La contraseña se almacena mediante Argon2id.
- El usuario se registra con estado activo y rol predeterminado `usuario`.
- La dirección es opcional.

Respuesta `201 Created`:

```json
{
  "id_usuario": 15,
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan@example.com",
  "estado": true,
  "fecha_registro": "2026-11-03T15:00:00",
  "fecha_actualizacion": null,
  "ultimo_acceso": null,
  "id_rol": 1,
  "telefono": "987654321",
  "direccion": "Av. Principal 123",
  "fecha_nacimiento": "2000-05-15",
  "rol": "usuario"
}
```

La respuesta no incluye la contraseña ni su hash.

### 3.2. Iniciar sesión

```http
POST /api/auth/login
Content-Type: application/json
```

Permite autenticar a un usuario mediante correo y contraseña.

Solicitud:

```json
{
  "email": "juan@example.com",
  "password": "Clave1234"
}
```

Respuesta `200 OK`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Reglas:

- Las cuentas inactivas no pueden iniciar sesión.
- Las credenciales incorrectas devuelven un mensaje genérico.
- Se bloquean nuevos intentos después de tres intentos fallidos durante 15 minutos.
- El último acceso se actualiza cuando el inicio de sesión es exitoso.

**Consideración técnica:** los intentos fallidos se almacenan actualmente en memoria del proceso. No son persistentes y no se comparten entre réplicas del backend.

### 3.3. Consultar perfil propio

```http
GET /api/users/me
Authorization: Bearer <jwt>
```

Permite consultar la información del usuario autenticado.

Respuesta `200 OK`:

```json
{
  "id_usuario": 15,
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan@example.com",
  "estado": true,
  "fecha_registro": "2026-11-03T15:00:00",
  "fecha_actualizacion": null,
  "ultimo_acceso": "2026-11-03T15:05:00",
  "id_rol": 1,
  "telefono": "987654321",
  "direccion": "Av. Principal 123",
  "fecha_nacimiento": "2000-05-15",
  "rol": "usuario"
}
```

Reglas:

- Requiere un JWT válido y no expirado.
- El usuario solo puede consultar su propio perfil.
- Si la cuenta está inactiva, el acceso es rechazado.
- No se exponen contraseñas ni hashes.

**Importante para otros microservicios:** esta operación no permite consultar a cualquier usuario mediante su identificador. El servicio identifica al usuario mediante el correo contenido en el JWT.

### 3.4. Actualizar perfil propio

```http
PUT /api/users/me
Authorization: Bearer <jwt>
Content-Type: application/json
```

Permite actualizar los datos personales del usuario autenticado.

Campos modificables:

- `nombre`
- `apellido`
- `email`
- `telefono`
- `direccion`
- `fecha_nacimiento`

No permite modificar el identificador, el rol, el estado ni el hash de contraseña.

Respuesta `200 OK`: devuelve el perfil actualizado con la misma estructura de la consulta de perfil.

### 3.5. Comprobar salud

```http
GET /api/health
```

Respuesta `200 OK`:

```json
{
  "status": "ok"
}
```

Esta ruta comprueba la disponibilidad del proceso FastAPI. No garantiza por sí sola que MariaDB esté disponible.

## 4. Integración con otros microservicios

### 4.1. Consulta de identidad y estado

Un microservicio como billetera o retiros puede necesitar verificar que un usuario exista y esté activo.

El identificador principal del usuario es:

```json
{
  "id_usuario": 15
}
```

El campo `estado` indica si la cuenta está activa:

| Estado | Significado |
|---|---|
| `true` | Usuario activo |
| `false` | Usuario inactivo |

### 4.2. Consultar estado por identificador

Endpoint implementado:

```http
GET /internal/users/{id_usuario}
X-API-Key: <api-key>
```

Permisos requeridos: `users:read_status`.

Los consumidores autorizados llaman directamente al backend usando
`http://users-api.app-pagos.svc.cluster.local:8000`. No deben invocar esta ruta
a través del Gateway Nginx, que devuelve 404 para `/internal` y `/internal/`.

Respuesta `200 OK`:

```json
{
  "id_usuario": 15,
  "estado": true
}
```

La respuesta solo contiene el identificador y el estado. No expone nombre,
correo, teléfono, dirección ni otros datos personales.

Respuestas relevantes:

- `401 Unauthorized`: falta la API Key o no corresponde a un consumidor.
- `403 Forbidden`: consumidor deshabilitado o sin el permiso requerido.
- `404 Not Found`: el usuario no existe.

El Gateway Nginx bloquea externamente todas las rutas bajo `/internal/`.
Un usuario inactivo se devuelve con `200 OK` y `estado: false`, lo que permite
distinguirlo de uno inexistente. Los consumidores aplican sus propias reglas
de negocio.

## 5. Errores

Los siguientes códigos corresponden al comportamiento esperado o implementado según cada operación:

| Código | Significado |
|---|---|
| 200 | Operación realizada correctamente |
| 201 | Usuario registrado |
| 400 | Solicitud inválida o contraseña que no cumple la política |
| 401 | Credenciales incorrectas, token requerido, inválido o expirado |
| 403 | Operación no autorizada |
| 404 | Usuario o recurso no encontrado, cuando corresponda |
| 409 | Correo electrónico ya registrado |
| 422 | Error de validación de datos |
| 500 | Error interno del servidor |

Los errores no deben exponer contraseñas, hashes, claves JWT, consultas SQL ni trazas internas.

## 6. Comunicación interna

La comunicación entre microservicios se realizará dentro de la red de Kubernetes.

Condiciones:

- El backend FastAPI se expondrá mediante un Service de tipo `ClusterIP`.
- MariaDB no tendrá exposición pública.
- El gateway Nginx será el punto de entrada definido para las solicitudes de la aplicación.
- Las integraciones internas utilizarán
  `http://users-api.app-pagos.svc.cluster.local:8000`.
- No se utilizarán direcciones IP fijas como parte del contrato.
- Las llamadas internas protegidas usan `X-API-Key`, huellas SHA-256, consumidores
  habilitados y permisos explícitos.

## 7. Responsabilidades del microservicio

El microservicio de usuarios es responsable de:

- Registrar usuarios.
- Autenticar usuarios.
- Emitir JWT para sesiones de usuario.
- Consultar perfiles propios.
- Actualizar datos personales.
- Administrar el estado y rol de los usuarios.

No es responsable de:

- Administrar saldos.
- Registrar depósitos o retiros.
- Realizar transferencias.
- Administrar billeteras.
- Ejecutar operaciones financieras.

Cada microservicio debe conservar su propia lógica de negocio.

## 8. Documentación técnica

La documentación interactiva se encuentra disponible mediante FastAPI:

```text
/docs
```

La especificación OpenAPI se encuentra disponible en:

```text
/openapi.json
```

Los equipos consumidores deberán revisar esta documentación para conocer los modelos, validaciones, respuestas y rutas realmente implementadas.

## 9. Consideraciones operativas

- Los intentos fallidos de inicio de sesión se guardan en memoria; mantener una
  sola réplica de FastAPI hasta migrar ese estado a almacenamiento compartido y
  persistente.
- Las API Keys originales, sus secretos JWT y las contraseñas se proporcionan
  mediante Kubernetes Secret y nunca se guardan en Git.
- La disponibilidad pública HTTPS y su dominio corresponden a la infraestructura
  central, no a este microservicio.

**Estado:** la consulta interna por `id_usuario`, la autenticación de
microservicios y el DNS de Kubernetes descritos en este contrato ya están
implementados.