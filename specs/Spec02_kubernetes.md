
## 1. Contexto del proyecto

El proyecto es un microservicio de usuarios para una aplicación de pagos.

Tecnologías existentes:
- Python 3.13.
- FastAPI.
- SQLAlchemy.
- MariaDB 11.8.9.
- Docker.
- Nginx como API Gateway.
- JWT para autenticación.
- Argon2id para hashing de contraseñas.

El repositorio ya dispone de Dockerfile, docker-compose.yml y nginx.conf.

## 2. Objetivo

Desplegar el microservicio utilizando Kubernetes en un clúster de un solo nodo.

El entorno objetivo es AWS EC2 con Amazon Linux 2023. Se administrará Kubernetes mediante kubectl desde Windows 10.

## 3. Componentes Kubernetes

Definir los siguientes recursos en el namespace `app-pagos`:

1. Namespace: `app-pagos`.
2. Deployment para FastAPI.
3. Service ClusterIP para FastAPI.
4. StatefulSet para MariaDB.
5. Service ClusterIP para MariaDB.
6. PersistentVolumeClaim para conservar los datos.
7. Secret para contraseñas y JWT_SECRET_KEY.
8. ConfigMap para configuraciones no sensibles.
9. Deployment para Nginx.
10. Service ClusterIP para Nginx.

La arquitectura de EKS utiliza el gateway centralizado de App Pagos. Este
microservicio no se publica directamente ni incorpora frontend. Los Services
`users-api` y `users-gateway` son `ClusterIP`; la comunicación interna usa
`users-api:8000`.

## 4. Requisitos técnicos

- Utilizar la imagen MariaDB 11.8.9.
- Construir una imagen Docker del backend.
- Publicar la imagen en un registro accesible desde EC2.
- No almacenar contraseñas ni secretos en los manifiestos.
- No exponer MariaDB públicamente.
- Configurar correctamente DATABASE_URL para utilizar el nombre del Service de MariaDB.
- Configurar readinessProbe y livenessProbe en FastAPI.
- Comprobar la disponibilidad de MariaDB antes de iniciar operaciones que requieran conexión.
- Configurar almacenamiento persistente para MariaDB.
- Evitar ejecutar contenedores como root cuando sea viable.
- Mantener las rutas y endpoints existentes del microservicio.

## 5. Entregables

- Manifiestos YAML organizados en una carpeta `k8s/`.
- Documentación para construir y publicar la imagen.
- Procedimiento de despliegue con kubectl.
- Procedimiento para comprobar el estado de los Pods y Services.
- Procedimiento para acceder a la API.
- Pruebas de registro, autenticación y consulta de perfil.
- Procedimiento para comprobar que MariaDB conserva los datos tras reiniciar su Pod.
- Instrucciones de limpieza del despliegue.

## 6. Restricciones

No reescribir el microservicio.
No cambiar las operaciones existentes.
No introducir frontend React si todavía no existe en el repositorio.
No utilizar contraseñas de ejemplo como credenciales reales.
No asumir que el clúster tiene un Ingress Controller instalado.

Antes de implementar, analiza el código actual y verifica qué ajustes son realmente necesarios. Documenta cualquier incompatibilidad encontrada.

7. Análisis previo obligatorio

Antes de implementar:

Analizar el repositorio y su estructura.

Revisar Dockerfile, docker-compose.yml y nginx.conf.

Identificar las variables de entorno utilizadas por FastAPI.

Verificar la conexión SQLAlchemy con MariaDB.

Identificar cómo se inicializan las tablas.

Verificar si existe un endpoint de salud para las probes.

Comprobar la compatibilidad de las imágenes con la arquitectura de EC2.

Identificar incompatibilidades entre Docker Compose y Kubernetes.

No realizar cambios hasta presentar un diagnóstico de compatibilidad.

El diagnóstico debe indicar:

Archivos compatibles.

Archivos que necesitan ajustes.

Variables de entorno necesarias.

Dependencias de infraestructura.

Riesgos de seguridad.

Cambios mínimos requeridos.

Después del diagnóstico, implementar únicamente los cambios necesarios para cumplir este SPEC.

## 8. Acceso público y consumo externo de la API

### 8.1. Objetivo

Permitir que aplicaciones y usuarios externos puedan consumir los endpoints del microservicio de usuarios a través de Internet.

Los consumidores podrán ser:

- Aplicaciones web.
- Aplicaciones móviles.
- Otros microservicios.
- Clientes HTTP como Postman.
- Sistemas externos autorizados.

### 8.2. Exposición de la API

- Nginx será el único punto de entrada público.
- FastAPI permanecerá expuesto únicamente mediante un Service ClusterIP.
- MariaDB permanecerá dentro de la red interna del clúster.
- Usar un Service ClusterIP para el gateway central.
- Permitir el tráfico correspondiente en el Security Group de EC2.
- Documentar la URL pública de acceso a la API.

### 8.3. Comunicación segura

- Configurar HTTPS mediante un certificado TLS válido.
- Evitar transmitir credenciales y tokens mediante HTTP sin cifrado.
- Configurar Nginx para redirigir HTTP a HTTPS cuando HTTPS esté habilitado.
- Mantener JWT para autenticar las solicitudes protegidas.
- Configurar los encabezados necesarios para el funcionamiento del proxy.

### 8.4. Consumo de la API

- Mantener los endpoints existentes.
- Permitir que clientes externos realicen solicitudes HTTP a los endpoints publicados.
- Documentar los métodos HTTP, rutas, parámetros, cuerpos de solicitud y respuestas.
- Proporcionar ejemplos de consumo mediante curl y Postman.
- Documentar el mecanismo de autenticación JWT.
- Mantener disponible la documentación OpenAPI de FastAPI, según la política de acceso definida.

### 8.5. Seguridad del acceso público

- No exponer directamente FastAPI ni MariaDB.
- No permitir acceso público al puerto 3306.
- No publicar secretos ni credenciales.
- Configurar CORS únicamente para los orígenes que realmente necesiten acceder desde navegadores.
- No considerar CORS como mecanismo de autenticación.
- Configurar límites de solicitudes en Nginx cuando sea viable.
- Evitar que los endpoints protegidos puedan utilizarse sin autenticación.
- Documentar qué endpoints son públicos y cuáles requieren JWT.

### 8.6. Pruebas de acceso externo

- Consumir la API desde una máquina distinta a la instancia EC2.
- Comprobar los endpoints mediante Postman y curl.
- Verificar el registro y autenticación de usuarios.
- Verificar el acceso a endpoints protegidos utilizando JWT.
- Comprobar que MariaDB y FastAPI no sean accesibles directamente desde Internet.
- Verificar el funcionamiento mediante HTTPS.