# SPEC-04: Preparación final del microservicio de usuarios para EKS

## Contexto

Repositorio: `RenzoAyvar/microservicio_usuarios`

El proyecto es un microservicio backend API desarrollado con FastAPI, SQLAlchemy y MariaDB. Se desplegará en Amazon EKS.

Namespace: `app-pagos`.

La arquitectura utiliza un frontend centralizado y un API Gateway central. El microservicio de usuarios no debe incorporar frontend ni exponerse directamente a Internet.

## Objetivo

Auditar y corregir los archivos existentes para dejar el proyecto listo para construir su imagen Docker y desplegarlo en EKS.

## Tareas

1. Revisar el código de `app/`, `tests/`, `Dockerfile` y todos los archivos de `k8s/`.
2. Corregir las pruebas para que validen correctamente las huellas SHA-256 de API Keys.
3. Añadir pruebas para API Keys incorrectas y validación de configuración de producción.
4. Verificar que las pruebas ejecuten correctamente el ciclo de vida de FastAPI y no dependan de comportamientos accidentales de TestClient.
5. Revisar que `APP_ENV=production` impida el uso de configuraciones inseguras.
6. Mantener `users-api` como Service `ClusterIP`, puerto 8000.
7. Mantener MariaDB como StatefulSet con PVC gp3 de 10 GiB.
8. Mantener `reclaimPolicy: Delete` en StorageClass.
9. Mantener Nginx como ClusterIP y bloquear `/internal` desde su entrada.
10. Mantener la comunicación interna directa mediante el DNS de `users-api`.
11. Actualizar `Spec03_contrato_api.md` con la implementación real de `X-API-Key`, el permiso `users:read_status` y el endpoint `/internal/users/{id_usuario}`.
12. Actualizar `Spec02_kubernetes.md` para reflejar el namespace `app-pagos`, los Services ClusterIP y la arquitectura de gateway central.
13. Revisar y corregir `k8s/README.md`, incluyendo la creación de secretos, construcción de imagen ECR y comandos de despliegue.
14. Confirmar que ningún secreto real se almacene en Git.
15. Revisar el `.dockerignore` para evitar copiar archivos innecesarios o secretos a la imagen.

## Restricciones

- No agregar frontend.
- No introducir NodePort ni LoadBalancer para `users-api`.
- No modificar los endpoints funcionales existentes sin justificación.
- No cambiar JWT por API Keys ni mezclar sus responsabilidades.
- No eliminar la protección del endpoint interno.
- No aumentar las réplicas de FastAPI mientras los intentos fallidos permanezcan en memoria.
- No modificar ni desplegar recursos AWS.
- No ejecutar `kubectl apply`.
- No publicar imágenes en ECR.

## Verificación requerida

Ejecutar las pruebas automatizadas y revisar los manifiestos YAML.

Entregar:
- Archivos modificados.
- Problemas encontrados y corregidos.
- Resultado de las pruebas.
- Comandos para construir y publicar la imagen.
- Procedimiento final de despliegue en EKS.
- Problemas pendientes que impidan un despliegue seguro.

No afirmar que el proyecto está listo si las pruebas no se ejecutaron satisfactoriamente.