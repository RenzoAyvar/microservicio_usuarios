
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

## 2. Entorno implementado

El microservicio se despliega en Amazon EKS `usuarios-eks`, región
`us-east-1`, namespace `app-pagos`. Se administra mediante `kubectl`; la
documentación operativa incluye instrucciones para Windows 10 CMD y PowerShell.

## 3. Componentes Kubernetes

Definir los siguientes recursos en el namespace `app-pagos`:

1. Namespace: `app-pagos`.
2. Deployment para FastAPI.
3. Service ClusterIP para FastAPI.
4. StatefulSet para MariaDB.
5. Service ClusterIP para MariaDB.
6. PVC de 10 GiB para conservar los datos de MariaDB.
7. Secret para contraseñas y JWT_SECRET_KEY.
8. ConfigMap para configuraciones no sensibles.
9. Deployment para Nginx.
10. Service ClusterIP para Nginx.

MariaDB se ejecuta como StatefulSet y utiliza un PVC `ReadWriteOnce` con
StorageClass `gp3`, cifrado EBS y AWS EBS CSI Driver. El StorageClass conserva
`reclaimPolicy: Delete`. FastAPI parte con una sola réplica porque
`FAILED_LOGINS` reside en memoria. Nginx actúa como gateway interno.

La arquitectura utiliza el gateway centralizado de App Pagos. Este
microservicio no se publica directamente ni incorpora frontend. Los Services
`users-api` y `users-gateway` son `ClusterIP`; los consumidores internos llaman
`http://users-api.app-pagos.svc.cluster.local:8000`. No se usan NodePort ni
LoadBalancer.

## 4. Requisitos técnicos

- Utilizar la imagen MariaDB 11.8.9.
- Construir y publicar la imagen del backend en ECR con una etiqueta basada
  en el SHA del commit.
- No almacenar contraseñas ni secretos en los manifiestos.
- No exponer MariaDB públicamente.
- Configurar `DATABASE_URL` con el Service `mariadb` dentro de `app-pagos`.
- La readiness de FastAPI consulta la base de datos; la liveness verifica el
  proceso sin depender de MariaDB.
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
No asumir que el clúster tiene un Ingress Controller instalado. No crear
Services `NodePort` o `LoadBalancer` ni exponer directamente FastAPI o MariaDB.
La publicación HTTPS corresponde a la infraestructura central.

El diseño desplegado mantiene los recursos anteriores internos al clúster. La
publicación pública HTTPS, el nombre de dominio, el certificado y la conexión
con el gateway centralizado pertenecen a la infraestructura central; no se
configuran en este microservicio.

## 7. Estado de compatibilidad

- Los manifiestos usan el namespace `app-pagos`; los Services de FastAPI,
  MariaDB y Nginx son `ClusterIP`.
- MariaDB es un StatefulSet con PVC de 10 GiB, `ReadWriteOnce`, StorageClass
  `gp3`, cifrado EBS y AWS EBS CSI Driver.
- El StorageClass tiene `reclaimPolicy: Delete`. Eliminar el StatefulSet no
  elimina necesariamente los PVC creados por `volumeClaimTemplates`.
- FastAPI utiliza readiness `/api/ready`, liveness `/api/live` y una réplica.
- Nginx bloquea `/internal` y `/internal/`; los consumidores autorizados llaman
  directamente al Service DNS `users-api`.
- Antes de escalar FastAPI, el contador `FAILED_LOGINS` en memoria debe
  trasladarse a almacenamiento compartido y persistente.
- Tras eliminar recursos, verificar por separado volúmenes EBS y otros recursos
  AWS residuales; eliminar el clúster no garantiza su eliminación.