Necesito preparar mi proyecto microservicio_usuarios para desplegarlo en Amazon EKS.

Entorno:

- Windows 10 desde donde administro el clúster con kubectl.
- Amazon EKS.
- Región: us-east-1.
- Kubernetes: 1.37.
- Un nodo de trabajo t3.medium.
- MariaDB como base de datos.
- FastAPI como backend.
- Nginx como API Gateway.
- Namespace: servicio_usuarios.
Mi configuración de entorno actual contiene:

- DATABASE_URL
- JWT_SECRET_KEY
- JWT_ALGORITHM
- ACCESS_TOKEN_EXPIRE_HOURS
- CORS_ORIGINS
- INTERNAL_SERVICE_CREDENTIALS
Necesito que inspecciones el repositorio y generes los manifiestos Kubernetes necesarios, adaptándolos al código real. No inventes endpoints, variables, nombres de módulos ni comandos de inicio.

Requisitos:

1. Crear una carpeta k8s/ con los manifiestos organizados.
2. Crear Namespace app-pagos.
3. Crear ConfigMap para las variables no sensibles.
4. Crear Secret para DATABASE_URL, JWT_SECRET_KEY e INTERNAL_SERVICE_CREDENTIALS.
5. Desplegar MariaDB mediante StatefulSet y PVC.
6. Crear Service interno para MariaDB con nombre mariadb.
7. Configurar persistencia mediante StorageClass gp3.
8. Desplegar FastAPI mediante Deployment y Service ClusterIP.
9. Desplegar Nginx mediante Deployment y Service.
10. No exponer MariaDB ni FastAPI directamente a Internet.
11. El endpoint /internal/users/{id_usuario} debe permanecer interno y no debe publicarse mediante el API Gateway.
12. Mantener la autenticación JWT personal separada de la autenticación mediante API Keys entre microservicios.
13. Configurar las variables de entorno utilizando los nombres exactos que espera el código.
14. Agregar readinessProbe y livenessProbe utilizando endpoints existentes.
15. Configurar requests y limits de CPU y memoria adecuados para un único nodo t3.medium.
16. Evitar credenciales escritas directamente en los YAML.
17. Documentar cómo construir las imágenes Docker y publicarlas en Amazon ECR.
18. Documentar cómo aplicar los manifiestos con kubectl y cómo verificar el despliegue.
19. Crear instrucciones para probar registro, login, consulta del perfil y consulta interna con API Key válida e inválida.
Importante:

- Primero inspecciona Dockerfiles, docker-compose, código FastAPI, configuración de MariaDB, Nginx y variables de entorno.
- Comprueba si la aplicación tiene problemas al funcionar con varias réplicas, especialmente el almacenamiento en memoria de intentos fallidos de login.
- No cambies la lógica funcional del proyecto sin justificarlo.
- No inventes contraseñas ni API Keys.
- No utilices localhost para conectar FastAPI con MariaDB.
- Usa nombres DNS internos de Kubernetes.
- Los manifiestos deben ser portables y no depender de recursos exclusivos de AWS, salvo el aprovisionamiento de almacenamiento EBS mediante CSI.
- No uses NodePort ni LoadBalancer para publicar el microservicio de usuarios.
- Si necesitas exponer el gateway, deja esa decisión documentada y separada del acceso interno.
Entregables:

- Carpeta k8s/ completa.
- Manifiestos YAML.
- Guía de despliegue en README.
- Comandos para construir y publicar imágenes en ECR.
- Guía de pruebas funcionales.
- Relación de cambios realizados respecto al Spec_usuarios_2.md
Antes de implementar cambios que alteren la lógica del backend, explícame qué necesitas modificar y por qué.