# Kubernetes - Microservicio de Usuarios

## Diagnostico previo

- Compatible: Dockerfile usa Uvicorn con `app.main:app`; compose y Nginx muestran los nombres y puertos reales.
- Compatible: SQLAlchemy crea las tablas al iniciar FastAPI mediante `Base.metadata.create_all`.
- Compatible: el endpoint de salud es `GET /api/health`.
- Compatible: MariaDB usa el puerto interno 3306.
- Ajuste requerido: el almacenamiento de intentos fallidos está en memoria (`FAILED_LOGINS`) y por eso FastAPI debe ejecutarse con una sola réplica.
- Ajuste requerido: Docker Compose usa el host `mariadb`; Kubernetes usa el Service DNS `mariadb`.
- Seguridad: los manifiestos no contienen credenciales. Se crean fuera del repositorio mediante `kubectl`.
- Seguridad: JWT y API Keys entre servicios permanecen separados. Las API Keys se configuran como huellas SHA-256 en `INTERNAL_SERVICE_CREDENTIALS`.

## Recursos

- Namespace: `app-pagos`
- Base de datos: `mariadb`, persistencia gp3 de 10 GiB
- Backend: `users-api`, ClusterIP en el puerto 8000
- Gateway: `users-gateway`, ClusterIP en el puerto 80

`users-api` y MariaDB no se publican. El Gateway no publica `/internal/`. Para publicar el gateway fuera del cluster, se requiere una decisión posterior: Ingress HTTPS o un Service administrado por AWS; ninguno se incluye aquí.

## Requisitos

- EKS con el CSI driver de EBS habilitado.
- Driver de red y acceso a imágenes oficiales configurados.
- El `StorageClass gp3` usa `ebs.csi.aws.com`, por lo que requiere el CSI addon de AWS para EBS.

La región configurada es `us-east-1`. Si la arquitectura de la instancia exige otra imagen de plataforma, construye y publica una imagen compatible con el nodo.

## Variables de configuracion

No sensibles:

- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_HOURS`
- `CORS_ORIGINS`

Sensibles:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `INTERNAL_SERVICE_CREDENTIALS`
- `MARIADB_PASSWORD`
- `MARIADB_ROOT_PASSWORD`

Ejemplos de valores reales se mantienen fuera de los YAML. Genera secretos mediante variables locales, sin escribirlos en un archivo:

```powershell
$MARIADB_PASSWORD = Read-Host -MaskInput "MariaDB application password"
$MARIADB_ROOT_PASSWORD = Read-Host -MaskInput "MariaDB root password"
$JWT_SECRET_KEY = Read-Host -MaskInput "JWT secret"

# La URL debe usar el Service DNS del cluster, no localhost.
$DATABASE_URL = "mysql+pymysql://appuser:$MARIADB_PASSWORD@mariadb:3306/app_pagos_usuarios"

# INTERNAL_SERVICE_CREDENTIALS debe ser JSON y contener huellas SHA-256 de API Keys.
$INTERNAL_SERVICE_CREDENTIALS = Read-Host -Prompt "Internal consumers JSON"

kubectl create namespace app-pagos --dry-run=client -o yaml | kubectl apply -f -

kubectl -n app-pagos create secret generic users-secrets `
  --from-literal=MARIADB_PASSWORD="$MARIADB_PASSWORD" `
  --from-literal=MARIADB_ROOT_PASSWORD="$MARIADB_ROOT_PASSWORD" `
  --from-literal=DATABASE_URL="$DATABASE_URL" `
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" `
  --from-literal=INTERNAL_SERVICE_CREDENTIALS="$INTERNAL_SERVICE_CREDENTIALS" `
  --dry-run=client -o yaml | kubectl apply -f -
```

Para generar una huella de API Key:

```powershell
$apiKey = Read-Host -MaskInput "API Key"
[Convert]::ToHexString([Security.Cryptography.SHA256.HashData([Text.Encoding]::UTF8.GetBytes("$apiKey"))).ToLowerInvariant()
```

Ejemplo de estructura JSON, sustituyendo la huella calculada:

```json
{
  "pagos-service": {
    "key_hashes": ["HUELLA_SHA256"],
    "permissions": ["users:read_status"],
    "enabled": true
  }
}
```

## Construir y publicar la imagen en ECR

Desde la raíz del repositorio:

```powershell
$AWS_REGION = "us-east-1"
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_REPOSITORY = "microservicio-usuarios"
$IMAGE_TAG = git rev-parse --short HEAD
$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"

aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>$null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
}

aws ecr get-login-password --region $AWS_REGION |
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$ECR_URI:$IMAGE_TAG" .
docker push "$ECR_URI:$IMAGE_TAG"
```

Actualiza el Deployment con la imagen publicada antes de aplicar:

```powershell
$IMAGE = "$ECR_URI:$IMAGE_TAG"
(Get-Content k8s/fastapi.yaml) -replace "REPLACE_WITH_ECR_IMAGE_URI", $IMAGE |
  Set-Content k8s/fastapi.rendered.yaml
kubectl apply -f k8s/fastapi.rendered.yaml
```

No publiques `fastapi.rendered.yaml` si puede contener datos sensibles por extensión posterior; la imagen no contiene credenciales.

## Aplicar los manifiestos

Aplica primero el namespace, almacenamiento, configuración, base de datos y backend/gateway:

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/storageclass-gp3.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Reemplaza el Secret vacío por uno creado con kubectl, como se indicó arriba.
kubectl apply -f k8s/mariadb.yaml
kubectl apply -f k8s/fastapi.yaml
kubectl apply -f k8s/nginx.yaml
```

O aplica todos los recursos y reemplaza después la imagen:

```powershell
kubectl apply -f k8s/
kubectl set image deployment/users-api users-api="$IMAGE" -n app-pagos
```

## Verificacion

```powershell
kubectl get pods,svc,pvc -n app-pagos
kubectl get storageclass gp3
kubectl rollout status deployment/users-api -n app-pagos
kubectl rollout status deployment/users-gateway -n app-pagos
kubectl rollout status statefulset/mariadb -n app-pagos
kubectl get endpoints -n app-pagos
kubectl logs deployment/users-api -n app-pagos
kubectl logs statefulset/mariadb -n app-pagos
```

Como los Services son internos, realiza pruebas mediante port-forward:

```powershell
kubectl port-forward -n app-pagos service/users-gateway 8080:80
```

FastAPI queda disponible en `http://127.0.0.1:8080`.

## Pruebas funcionales

Los JSON siguientes usan valores de prueba locales. Sustituye el correo y la contraseña.

Registro:

```powershell
curl.exe -X POST http://127.0.0.1:8080/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"nombre\":\"Ana\",\"apellido\":\"Perez\",\"email\":\"ana@example.com\",\"password\":\"Clave123!\",\"telefono\":\"999999999\",\"direccion\":\"Lima\",\"fecha_nacimiento\":\"1990-01-01\"}'
```

Login:

```powershell
$login = curl.exe -X POST http://127.0.0.1:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"ana@example.com\",\"password\":\"Clave123!\"}'
$login | ConvertFrom-Json
$TOKEN = ($login | ConvertFrom-Json).access_token
```

Perfil:

```powershell
curl.exe http://127.0.0.1:8080/api/users/me `
  -H "Authorization: Bearer $TOKEN"
```

Consulta interna válida e inválida. La consulta directa debe hacerse mediante acceso interno al backend o mediante port-forward de FastAPI; el gateway debe devolver 404.

```powershell
# El gateway no debe publicar la ruta interna.
curl.exe -i http://127.0.0.1:8080/internal/users/1

# Iniciar otro port-forward durante las pruebas internas.
kubectl port-forward -n app-pagos service/users-api 8000:8000

curl.exe -i http://127.0.0.1:8000/internal/users/1 `
  -H "X-API-Key: $VALID_API_KEY"

curl.exe -i http://127.0.0.1:8000/internal/users/1 `
  -H "X-API-Key: api-key-invalida"
```

La clave válida debe ser la clave original cuya huella esté configurada. Nunca publiques la clave real en repositorios, comandos históricos o YAML.

## Persistencia

Comprueba que MariaDB conserva los datos:

```powershell
kubectl delete pod mariadb-0 -n app-pagos
kubectl rollout status statefulset/mariadb -n app-pagos
kubectl port-forward -n app-pagos service/users-gateway 8080:80
```

Después inicia sesión o consulta el perfil nuevamente.

## Relacion con Spec_usuarios_2.md

- Se mantiene la separación JWT/API Key definida por el spec.
- Se mantienen los endpoints reales registrados en el código.
- Se implementa la ruta interna sin publicación en Nginx.
- Se mantiene una réplica de FastAPI por la limitación de intentos fallidos en memoria; el spec exige consistencia si hay varias réplicas.
- Docker Compose no se modifica: sus credenciales de desarrollo siguen siendo específicas de desarrollo y no se reutilizan en Kubernetes.
- Se añade producción Kubernetes sobre los recursos existentes sin cambiar la lógica funcional.
- La exposición HTTPS pública queda fuera de los manifiestos, para evitar asumir un Ingress Controller o un método de publicación.
