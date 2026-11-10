# SPEC-05: Correcciones finales de pruebas, seguridad y documentación para despliegue en Kubernetes

## 1. Contexto del proyecto

**Repositorio:** `RenzoAyvar/microservicio_usuarios`

**Rama:** `main`

**Arquitectura:** Microservicio de usuarios basado en FastAPI, SQLAlchemy y MariaDB, preparado para ejecutarse en Kubernetes sobre Amazon EKS.

**Infraestructura objetivo:**
- Clúster EKS: `usuarios-eks`.
- Región AWS: `us-east-1`.
- Namespace: `app-pagos`.
- Backend: `users-api`, Service ClusterIP, puerto 8000.
- Gateway: `users-gateway`, Service ClusterIP, puerto 80.
- Base de datos: MariaDB 11.8.9.
- Almacenamiento: EBS gp3 mediante AWS EBS CSI Driver.

## 2. Objetivo principal

Realizar una última corrección del repositorio antes de iniciar la construcción de la imagen Docker y su publicación en Amazon ECR.

Se deben solucionar los problemas identificados en la revisión del repositorio:

1. Evitar que se aplique accidentalmente un Secret vacío.
2. Eliminar las instrucciones que aplican indiscriminadamente todos los manifiestos Kubernetes.
3. Mejorar el aislamiento y la determinación de las pruebas automatizadas.
4. Corregir la configuración CORS de ejemplo.
5. Actualizar la documentación SPEC para que coincida con el código implementado.
6. Adaptar la documentación de despliegue a Windows 10, diferenciando CMD de PowerShell.
7. Comprobar que el procedimiento de despliegue no utiliza imágenes placeholder ni publica servicios individuales.

## 3. Restricciones obligatorias

No modificar la arquitectura general.

No agregar frontend al microservicio.

No convertir los Services ClusterIP en NodePort o LoadBalancer.

No exponer directamente FastAPI ni MariaDB a Internet.

No eliminar ni modificar la autenticación JWT existente.

No reemplazar la autenticación API Key entre microservicios.

No cambiar el contrato funcional de los endpoints existentes, salvo que se detecte una inconsistencia demostrable.

No introducir nuevas dependencias sin justificación técnica.

No modificar Docker Compose innecesariamente.

No realizar operaciones sobre AWS ni sobre el clúster EKS.

No ejecutar `eksctl`, `aws eks`, `kubectl apply`, `kubectl delete`, `docker push` ni operaciones que modifiquen recursos externos.

El trabajo debe limitarse al repositorio local, sus pruebas y su documentación.

## 4. Corrección de las pruebas automatizadas

Archivo principal: `tests/test_user_service.py`.

### 4.1. Corregir la API Key inicial de pruebas

Actualmente existe una configuración inicial con un hash inválido:

`test-key-hash`

Debe sustituirse por una huella SHA-256 real de una clave de prueba.

Ejemplo conceptual:

- API Key de prueba: `pagos-api-key`.
- Huella: `hashlib.sha256(b"pagos-api-key").hexdigest()`.

La configuración inicial de pruebas debe cumplir exactamente las mismas validaciones que exige la aplicación.

No desactivar ni debilitar las validaciones de producción para conseguir que las pruebas pasen.

### 4.2. Aislar la configuración entre pruebas

Actualmente algunas pruebas modifican la configuración global mediante `set_service_credentials()`.

Esto puede provocar dependencias entre pruebas y resultados diferentes según el orden de ejecución.

Corregir mediante fixtures de pytest o un mecanismo equivalente que garantice:

- Cada prueba recibe una configuración conocida.
- Las modificaciones globales se restauran al finalizar.
- Ninguna prueba depende de otra.
- Las pruebas pueden ejecutarse individualmente.
- Las pruebas pueden ejecutarse en cualquier orden.

### 4.3. Probar correctamente el lifespan de FastAPI

El proyecto utiliza el ciclo de vida `lifespan`.

Todas las pruebas que necesiten validar el inicio de FastAPI deben utilizar correctamente el administrador de contexto de `TestClient`.

Comprobar que:

- La configuración se valida durante el inicio.
- La inicialización de la aplicación funciona.
- La aplicación puede cerrarse correctamente.
- Una configuración inválida impide iniciar la aplicación.
- Una configuración válida permite iniciar la aplicación.

No mantener una instancia global de TestClient que provoque contaminación entre pruebas.

### 4.4. Casos que deben mantenerse o añadirse

Mantener las pruebas existentes de:

- Registro de usuarios.
- Inicio de sesión.
- Consulta y actualización del perfil.
- Rechazo de correo duplicado.
- Rechazo de contraseña inválida.
- Bloqueo después de tres intentos fallidos.
- Autenticación interna mediante API Key.
- Rechazo de API Key incorrecta.
- Rechazo de consumidores deshabilitados.
- Rechazo de permisos insuficientes.
- Ocultamiento de información personal.
- Diferenciación entre usuario inactivo y usuario inexistente.
- Bloqueo de rutas `/internal/` en Nginx.
- Inicio del lifespan.

Agregar o reforzar pruebas para:

- Hash de API Key con formato inválido.
- Configuración JSON inválida.
- Configuración de consumidor incompleta.
- Configuración de producción con SQLite.
- Configuración de producción con JWT predeterminado.
- Inicio de aplicación con configuración inválida.

### 4.5. Criterio de aceptación

Ejecutar:

`pytest -q`

Resultado esperado:

- Todas las pruebas pasan.
- Ninguna prueba depende del orden de ejecución.
- Las pruebas de lifespan funcionan individualmente.
- No se omiten validaciones de seguridad.

Entregar también el resultado de una ejecución individual de las pruebas críticas.

## 5. Corregir la configuración CORS

Archivo: `k8s/configmap.yaml`.

Actualmente:

`CORS_ORIGINS: "https://example.invalid"`

Este valor es un placeholder y no debe presentarse como configuración lista para producción.

Realizar lo siguiente:

1. Documentar que debe sustituirse por el origen real del frontend centralizado.
2. Mantener un valor de ejemplo claramente identificado como ejemplo, no como dominio de producción.
3. Explicar que CORS depende del origen desde el que el navegador consume la API.
4. Si frontend y API se publican bajo el mismo origen mediante el gateway central, documentar cuándo puede no ser necesario habilitar CORS adicional.

No inventar el dominio definitivo del frontend.

## 6. Corregir el manejo de Secrets de Kubernetes

Archivos involucrados:

- `k8s/secret.yaml`
- `k8s/README.md`
- `README.md`, si contiene instrucciones equivalentes.

### 6.1. Mantener el manifiesto como plantilla

Se puede conservar `k8s/secret.yaml` como plantilla vacía, siempre que esté claramente identificado como archivo de referencia que NO debe aplicarse directamente.

Agregar comentarios explicativos:

- El archivo no contiene credenciales.
- No debe ejecutarse `kubectl apply -f k8s/secret.yaml`.
- El Secret real se crea por separado mediante `kubectl create secret generic`.
- Nunca deben guardarse credenciales reales en Git.

### 6.2. Secret obligatorio

El objeto `users-secrets` debe contener exactamente las siguientes claves requeridas por los manifiestos:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `INTERNAL_SERVICE_CREDENTIALS`
- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`

Comprobar que los nombres coincidan con las referencias `secretKeyRef` de FastAPI y MariaDB.

### 6.3. Procedimiento seguro de creación

Documentar un procedimiento reproducible que:

- Cree el namespace si todavía no existe.
- Solicite las credenciales al operador.
- Genere la huella SHA-256 de las API Keys.
- Construya el JSON de consumidores internos.
- Genere o actualice el Secret `users-secrets`.
- No escriba valores reales en archivos versionados.
- No imprima credenciales en pantalla.
- No sobrescriba accidentalmente el Secret con uno vacío.

Para la documentación de Windows, proporcionar instrucciones compatibles con PowerShell y explicar expresamente cuándo debe abrirse PowerShell en lugar de CMD.

Considerar el manejo de caracteres especiales en contraseñas, especialmente `$`, `!`, `\` y comillas.

No utilizar contraseñas de ejemplo como credenciales reales.

## 7. Corregir completamente el procedimiento de despliegue

Archivo principal: `k8s/README.md`.

Este apartado es especialmente importante.

### 7.1. Eliminar secuencias peligrosas

Eliminar instrucciones como:

`kubectl apply -f k8s/`

No debe existir ningún procedimiento recomendado que aplique indiscriminadamente todos los YAML de la carpeta.

Eliminar también la aplicación del Secret vacío.

No aplicar el Deployment de FastAPI mientras contenga:

`REPLACE_WITH_ECR_IMAGE_URI`

### 7.2. Orden obligatorio de despliegue

Documentar el siguiente orden:

**Fase 1. Verificaciones previas**

- Comprobar identidad AWS.
- Comprobar región `us-east-1`.
- Comprobar contexto de kubectl.
- Comprobar existencia del clúster `usuarios-eks`.
- Comprobar que el nodo está Ready.
- Comprobar que el addon EBS CSI está activo.
- Comprobar que existe el StorageClass `gp3`.

**Fase 2. Preparación de imagen**

- Crear el repositorio ECR si no existe.
- Construir la imagen Docker.
- Etiquetarla utilizando el SHA del commit.
- Autenticarse en ECR.
- Publicar la imagen.
- Verificar que la imagen publicada existe.

**Fase 3. Preparación de Kubernetes**

- Crear o comprobar namespace `app-pagos`.
- Aplicar `k8s/storageclass-gp3.yaml` únicamente si corresponde.
- Aplicar `k8s/configmap.yaml`.
- Crear o actualizar `users-secrets` con todas las claves necesarias.

**Fase 4. Despliegue de recursos**

- Aplicar `k8s/mariadb.yaml`.
- Esperar a que MariaDB esté Ready y su PVC esté Bound.
- Generar el manifiesto de FastAPI con la imagen ECR real.
- Aplicar `k8s/fastapi.yaml` ya renderizado con la imagen real.
- Esperar a que FastAPI esté Ready.
- Aplicar `k8s/nginx.yaml`.
- Esperar a que el gateway esté Ready.

Nunca aplicar un manifiesto con imagen placeholder.

### 7.3. Gestión de imagen

Documentar una forma de sustituir la imagen placeholder por una imagen ECR real.

El archivo renderizado debe:

- Generarse localmente.
- No contener credenciales.
- No sobrescribir el manifiesto original.
- No incluirse en Git.
- Ser eliminado o ignorado después de utilizarse.

Agregar validación que impida continuar si la imagen todavía contiene `REPLACE_WITH_ECR_IMAGE_URI`.

### 7.4. Comandos para Windows

El usuario trabaja principalmente desde Windows 10 CMD.

Proporcionar instrucciones para:

- CMD: Git, Docker, AWS CLI, ECR, kubectl y verificaciones.
- PowerShell: operaciones de captura de secretos y comandos que requieran sintaxis propia de PowerShell.

No presentar comandos de PowerShell como si fueran comandos compatibles con CMD.

Cuando un procedimiento requiera cambiar de terminal, indicarlo explícitamente.

## 8. Actualización de documentación SPEC

### 8.1. `specs/Spec03_contrato_api.md`

Actualizar el contrato para reflejar la implementación real.

Documentar:

- Header `X-API-Key`.
- Autenticación de servicios mediante API Keys.
- Almacenamiento de huellas SHA-256.
- Comparación segura de huellas.
- Consumidores y permisos.
- Permiso `users:read_status`.
- Rechazo de claves inválidas.
- Rechazo de consumidores deshabilitados.
- Endpoint `GET /internal/users/{id_usuario}`.
- Respuesta que contiene únicamente `id_usuario` y `estado`.
- Respuesta 404 para usuarios inexistentes.
- Separación entre JWT de usuarios y API Keys de servicios.
- Dirección DNS interna de Kubernetes.

DNS interno esperado:

`http://users-api.app-pagos.svc.cluster.local:8000`

Eliminar o actualizar las secciones que indican que el endpoint interno o la autenticación entre servicios todavía están pendientes.

### 8.2. `specs/Spec02_kubernetes.md`

Actualizar la documentación para reflejar:

- Namespace `app-pagos`.
- EKS `usuarios-eks`.
- Servicios ClusterIP.
- MariaDB StatefulSet.
- PVC de 10 GiB.
- StorageClass `gp3`.
- EBS CSI.
- FastAPI con una réplica inicial.
- Nginx como gateway interno.
- Ausencia de NodePort y LoadBalancer en el microservicio.

Eliminar referencias contradictorias a un namespace antiguo `usuarios` y a publicación mediante NodePort.

La exposición pública HTTPS debe quedar como una responsabilidad de la infraestructura central, no de este microservicio.

## 9. Verificar la configuración de MariaDB y FastAPI

Revisar los siguientes archivos:

- `k8s/mariadb.yaml`
- `k8s/fastapi.yaml`
- `k8s/nginx.yaml`
- `app/config.py`
- `app/database.py`
- `app/main.py`

Comprobar:

1. MariaDB usa el Service DNS `mariadb`.
2. FastAPI utiliza una `DATABASE_URL` que apunta a MariaDB dentro del namespace.
3. Las referencias de Secrets y ConfigMaps coinciden.
4. Las probes utilizan endpoints existentes.
5. El `startupProbe` permite un inicio suficientemente prolongado.
6. La readiness de FastAPI verifica disponibilidad de la base de datos.
7. La liveness no depende innecesariamente de MariaDB.
8. Nginx bloquea `/internal` y `/internal/`.
9. Los consumidores internos llaman directamente a `users-api`.
10. Los servicios no están expuestos mediante NodePort o LoadBalancer.

No cambiar las probes si ya cumplen correctamente estos requisitos.

### 9.1. Persistencia

Mantener:

- PVC de 10 GiB.
- StorageClass `gp3`.
- Cifrado EBS.
- `reclaimPolicy: Delete`.
- `ReadWriteOnce`.

Documentar que eliminar un StatefulSet no necesariamente elimina los PVC creados por `volumeClaimTemplates`.

No afirmar que eliminar el clúster garantiza por sí solo que todos los recursos AWS residuales desaparezcan. Documentar la verificación posterior de volúmenes EBS y otros recursos.

### 9.2. Intentos fallidos de inicio de sesión

Mantener una sola réplica de FastAPI mientras `FAILED_LOGINS` siga almacenándose en memoria.

No implementar Redis ni modificar la arquitectura en este SPEC.

Documentar que antes de escalar réplicas será necesario trasladar el contador a un almacenamiento compartido y persistente.

## 10. Verificación final del repositorio

Ejecutar las siguientes verificaciones locales:

### Pruebas

`pytest -q`

### Docker Compose

`docker compose config`

### Construcción Docker

`docker build -t microservicio-usuarios:spec05 .`

No publicar la imagen en ECR durante esta tarea.

### Validación YAML

Validar sintaxis de todos los manifiestos Kubernetes.

Utilizar `kubectl --dry-run=client` o una herramienta equivalente sin modificar el clúster.

No ejecutar `kubectl apply`.

### Seguridad

Comprobar que:

- No hay contraseñas reales en Git.
- No hay JWT secrets reales.
- No hay API Keys reales.
- `.env` está excluido.
- Los archivos renderizados están excluidos.
- No se introducen archivos de credenciales en el repositorio.
- Los manifiestos no contienen placeholders en una versión presentada como lista para desplegar.

### Arquitectura

Confirmar que:

- No existe NodePort.
- No existe LoadBalancer.
- No hay exposición directa de MariaDB.
- No se publica `/internal/` por Nginx.
- FastAPI continúa utilizando ClusterIP.
- MariaDB continúa utilizando almacenamiento persistente.

## 11. Criterios de aceptación

El SPEC-05 se considerará completado cuando:

1. Todas las pruebas automatizadas pasen.
2. Las pruebas sean independientes del orden de ejecución.
3. Docker Compose sea válido.
4. La imagen Docker pueda construirse localmente.
5. Todos los manifiestos YAML sean válidos.
6. El README no recomiende aplicar indiscriminadamente `k8s/`.
7. El Secret vacío no pueda confundirse con el Secret real.
8. El procedimiento de despliegue exija una imagen ECR real.
9. Los comandos estén diferenciados entre CMD y PowerShell.
10. Los documentos SPEC coincidan con la implementación.
11. No existan secretos reales rastreados.
12. La arquitectura ClusterIP se mantenga intacta.
13. No se hayan realizado cambios en AWS ni en EKS.

## 12. Entregables

Al finalizar, entregar:

- Archivos modificados.
- Resumen de cada corrección.
- Resultado completo de `pytest -q`.
- Resultado de `docker compose config`.
- Resultado de construcción Docker.
- Resultado de validación YAML.
- Confirmación de que no se ejecutaron operaciones sobre AWS o EKS.
- Lista de pendientes externos al repositorio.
- Commit generado y archivos incluidos.

## 13. Instrucción final al agente

Trabaja sobre la versión actual de la rama `main`.

Primero inspecciona el código y los documentos existentes. Después realiza los cambios mínimos necesarios para cumplir este SPEC-05.

No reescribas componentes que ya funcionan correctamente.

No modifiques la arquitectura del sistema.

No elimines funcionalidades existentes.

No inventes configuraciones de producción que todavía no han sido definidas.

Si encuentras una inconsistencia que no puedes resolver con la información disponible, documenta el problema en lugar de asumir una solución.

El resultado debe dejar el repositorio preparado para iniciar posteriormente la construcción y publicación de la imagen ECR y el despliegue controlado en EKS, pero sin ejecutar esas operaciones.