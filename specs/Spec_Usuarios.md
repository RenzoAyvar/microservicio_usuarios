# SPEC-001 — Microservicio de Usuarios para una Aplicación de Pagos

## 1. Información general

- **Proyecto:** App Pagos.
- **Módulo:** Microservicio de Usuarios.
- **Versión:** 0.1.
- **Tipo de sistema:** Aplicación web con arquitectura basada en microservicios.
- **Actor principal:** Usuario de la aplicación.
- **Estado:** Especificación inicial.

## 2. Objetivo

Desarrollar un módulo de usuarios que permita registrar cuentas, iniciar sesión, consultar información personal y actualizar los datos del perfil.

El sistema utilizará una aplicación frontend desarrollada con React, un backend en Python con FastAPI y una base de datos MariaDB. Las solicitudes del cliente pasarán por un API Gateway que actuará como punto de entrada al backend.

## 3. Tecnologías

-Frontend en React.
-Backend y API REST con Python y FastAPI.
-Api gateway con Nginx como proxy inverso.
-Base de datos con MariaDB 11.8.9.
-Comunicación con HTTP en desarrollo y HTTPS en producción.
-Autenticación con JWT.
-Hash de contraseñas con Argon2id.
-Acceso a datos con Pydantic.
-Pruebas con Pytest y pruebas manuales con Swagger UI.

FastAPI generará documentación interactiva de la API, accesible desde `/docs`, facilitando las pruebas sin necesidad de completar primero el frontend.

## 4. Arquitectura del sistema

La aplicación estará compuesta por cuatro capas lógicas:

1. **Cliente APP/Web:** interfaz desarrollada en React.
2. **API Gateway:** Nginx recibirá las solicitudes y las dirigirá al backend.
3. **Microservicio de Usuarios:** FastAPI implementará la lógica de negocio.
4. **Base de datos:** MariaDB almacenará los usuarios y sus roles.

Flujo general:

`React → Nginx API Gateway → FastAPI → MariaDB`

Las respuestas regresarán al cliente por el mismo recorrido. El gateway realizará el enrutamiento; el microservicio validará los datos, verificará los permisos y ejecutará las operaciones.

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
- La contraseña debe cumplir una política mínima de seguridad, 8 caracteres como mínimo y 16 como máximo,
debe tener al menos una letra mayúscula, una letra minuscula y al menos un número.
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
- Si las credenciales son incorrectas, se devolverá un mensaje genérico que no revele si el correo está registrado, solo dirá "Credenciales incorrectas".
- Luego de tres intentos fallidos la cuenta bloqueará nuevos intentos de acceso por 15 minutos.

El JWT será validado por el backend en las operaciones protegidas. No se almacenarán tokens de acceso en una tabla MariaDB en esta primera versión.

### RF-03. Consultar usuario

El sistema permitirá consultar la información del usuario autenticado.

Datos que se podrán mostrar:
- Identificador.
- Nombre y apellido.
- Correo electrónico.
- Estado de la cuenta.
- Fecha de registro.
- Último acceso.
- Rol.
- Teléfono, dirección y fecha de nacimiento.

Reglas:
- Será obligatorio presentar un JWT válido.
- La contraseña y el hash nunca aparecerán en la respuesta.
- En la primera versión, el usuario solo podrá consultar su propia información.
- Un usuario no podrá consultar ni modificar los datos de otra cuenta mediante el cambio del identificador.

### RF-04. Actualizar datos

El sistema permitirá actualizar los datos personales y del perfil del usuario autenticado.

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

El cambio de contraseña podrá añadirse como una funcionalidad independiente en una versión posterior.

RF-05 Consultar internamente un usuario mediante id_usuario.
RF-06 Permitir que microservicios autorizados consulten el estado de un usuario.
RF-07 Autenticar y autorizar las solicitudes entre microservicios.
RNF-01 La comunicación interna utilizará Kubernetes Services y DNS interno.
RNF-02 Las credenciales de integración se gestionarán mediante variables de entorno o Secrets.

## 6. Modelo de datos

La base de datos MariaDB se llamará `app_pagos_usuarios`.

### Tabla `rol`

-Campo 'id_rol' de tipo INT, restricción PK, autoincremental.
-Campo 'nombre' de tipo VARCHAR(50), restricción Único, no nulo.
-Campo 'descripcion' de tipo VARCHAR(50), restricción Opcional.

Roles iniciales:
- `usuario`
- `administrador`

### Tabla `usuario`

-Campo 'id_usuario' de tipo INT, restricción PK, autoincremental.
-Campo 'nombre' de tipo VARCHAR(100), restricción .
-Campo 'apellido' de tipo VARCHAR(100), restricción No nulo.
-Campo 'email' de tipo VARCHAR(150), restricción No nulo.
-Campo 'password_hash' de tipo VARCHAR(255), restricción No nulo.
-Campo 'estado' de tipo BOOLEAN, restricción No nulo, predeterminado verdadero.
-Campo 'fecha_registro' de tipo DATETIME, restricción no nulo.
-Campo 'fecha_actualizacion' de tipo DATETIME, restricción Opcional.
-Campo 'ultimo_acceso' de tipo DATETIME, restricción Opcional.
-Campo 'id_rol' de tipo INT, restricción FK a `rol.id_rol`, no nulo.
-Campo 'telefono' de tipo VARCHAR(20), restricción No nulo.
-Campo 'direccion' de tipo VARCHAR(150), restricción Opcional.
-Campo 'fecha_nacimiento' de tipo DATE, restricción No nulo.

Relación: un rol puede estar asociado a muchos usuarios; cada usuario tendrá un único rol.

Las tablas `perfil_usuario`, `usuario_rol`, `token` y `login_intento` no se crearán en esta versión.

## 7. API REST

Todos los endpoints se expondrán a través del prefijo `/api`.

Método, Endpoint, propósito y acceso:
| POST | `/api/auth/register` | Registrar usuario | Público |
| POST | `/api/auth/login` | Iniciar sesión | Público |
| GET | `/api/users/me` | Consultar perfil propio | Autenticado |
| PUT | `/api/users/me` | Actualizar perfil propio | Autenticado |
| GET | `/api/health` | Comprobar disponibilidad | Público |

El API Gateway dirigirá estas solicitudes al microservicio FastAPI. El endpoint de salud permitirá comprobar que el servicio está operativo; la comprobación de MariaDB podrá añadirse como una verificación separada.

### Respuestas esperadas

- `200 OK`: operación realizada correctamente.
- `201 Created`: usuario registrado.
- `400 Bad Request`: datos inválidos o conflicto de negocio.
- `401 Unauthorized`: credenciales incorrectas o token inválido.
- `403 Forbidden`: operación no permitida.
- `404 Not Found`: recurso inexistente.
- `409 Conflict`: correo ya registrado.
- `422 Unprocessable Entity`: errores de validación de entrada.
- `500 Internal Server Error`: error inesperado.

Los errores devolverán mensajes claros, sin exponer consultas SQL, contraseñas, tokens ni trazas internas.

## 8. Requisitos de seguridad

- Todas las contraseñas se almacenarán como hashes Argon2id.
- Los endpoints protegidos exigirán un JWT firmado y no expirado.
- La clave de firma se obtendrá de una variable de entorno y se incluirá en el repositorio.
- El JWT tendrá una duración limitada, definida mediante configuración.
- Las consultas a MariaDB utilizarán SQLAlchemy y parámetros seguros.
- Los datos de entrada se validarán mediante Pydantic.
- Se habilitará CORS únicamente para los orígenes autorizados.
- En producción se utilizará HTTP.
- Se limitarán las solicitudes de autenticación mediante el gateway o controles equivalentes.
- No se devolverá `password_hash` en ninguna respuesta pública.
- Los datos personales solo podrán ser consultados o modificados por el propietario de la cuenta, salvo operaciones administrativas expresamente autorizadas.

## 9. Requisitos no funcionales

- **Mantenibilidad:** separar rutas, modelos, esquemas, servicios y configuración.
- **Compatibilidad:** frontend y backend intercambiarán JSON mediante HTTP.
- **Integridad:** MariaDB aplicará claves primarias, foráneas y restricciones de unicidad.
- **Usabilidad:** los formularios mostrarán errores comprensibles.
- **Pruebas:** las operaciones principales tendrán pruebas automatizadas.
- **Configuración:** las credenciales de MariaDB, la clave JWT y los orígenes CORS se gestionarán mediante variables de entorno.

## 10. Fuera del alcance de la primera versión

- Gestión de pagos y transferencias.
- Recuperación de contraseña por correo.
- Verificación de correo electrónico.
- Autenticación de dos factores.
- Administración avanzada de roles.
- Registro persistente de intentos de inicio de sesión.
- Almacenamiento de sesiones o tokens en una tabla.
- Despliegue con Kubernetes o una plataforma de orquestación.

## 11. Criterios de aceptación

1. Un visitante puede registrar una cuenta con datos válidos.
2. El sistema rechaza correos duplicados.
3. Las contraseñas no se almacenan en texto plano.
4. Un usuario registrado puede iniciar sesión con sus credenciales correctas.
5. Un inicio de sesión incorrecto no devuelve un JWT válido.
6. Un usuario autenticado puede consultar sus propios datos.
7. Un usuario autenticado puede actualizar sus datos permitidos.
8. Las solicitudes protegidas sin JWT válido son rechazadas.
9. Ninguna respuesta expone el hash de la contraseña.
10. El frontend consume el backend a través del API Gateway.
11. Los datos persisten en MariaDB después de reiniciar el backend.
12. Los endpoints principales pueden probarse mediante Swagger UI y pruebas automatizadas.

## 12. Orden sugerido de implementación

1. Crear el repositorio y la estructura de carpetas.
2. Configurar MariaDB y crear las tablas `rol` y `usuario`.
3. Implementar el backend FastAPI y la conexión con MariaDB.
4. Implementar el registro y las validaciones.
5. Implementar el inicio de sesión, el hash de contraseñas y JWT.
6. Implementar la consulta y actualización del perfil.
7. Configurar Nginx como API Gateway.
8. Crear las pantallas React de registro, inicio de sesión y perfil.
9. Conectar el frontend con el gateway.
10. Ejecutar las pruebas funcionales y de seguridad.

**Resultado final esperado:** una aplicación web funcional de gestión de usuarios, con autenticación, perfiles, persistencia en MariaDB y una arquitectura organizada en las cuatro capas definidas.
