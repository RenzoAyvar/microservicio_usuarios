# Despliegue controlado en Amazon EKS

Esta guía es para el clúster `usuarios-eks`, región `us-east-1` y namespace
`app-pagos`. Los Services `users-api`, `users-gateway` y `mariadb` son
internos. No hay publicación directa de FastAPI ni MariaDB; la publicación
HTTPS es responsabilidad de la infraestructura central.

No ejecutar estas instrucciones durante una revisión local del repositorio.
Los comandos de esta guía son para una futura operación autorizada.

## CORS

`CORS_ORIGINS` en `configmap.yaml` contiene `http://localhost:3000` únicamente
como ejemplo local; no es un dominio de producción. Antes de desplegar,
sustituirlo por el origen real del frontend centralizado, incluyendo esquema y
puerto cuando corresponda. CORS controla qué orígenes de navegador pueden
leer respuestas; no autentica clientes. Si el gateway central sirve frontend
y API bajo el mismo origen, normalmente no se requiere habilitar CORS
adicional. No se presupone ni se inventa el dominio del frontend.

## Fase 1: verificaciones previas

Ejecutar en **CMD** desde una sesión autenticada. No continuar si la cuenta,
región, contexto o recursos no corresponden al entorno previsto.

```cmd
set AWS_REGION=us-east-1
aws sts get-caller-identity --region %AWS_REGION%
aws configure get region
aws eks describe-cluster --name usuarios-eks --region %AWS_REGION% --query cluster.status --output text
kubectl config current-context
kubectl get nodes -o wide
aws eks describe-addon --cluster-name usuarios-eks --addon-name aws-ebs-csi-driver --region %AWS_REGION% --query addon.status --output text
kubectl get storageclass gp3 -o yaml
```

Confirmar identidad y contexto esperados, región `us-east-1`, clúster con
estado `ACTIVE`, al menos un nodo `Ready`, addon EBS CSI `ACTIVE` y
StorageClass `gp3` con provisionador `ebs.csi.aws.com`, tipo `gp3`, cifrado y
`reclaimPolicy: Delete`. Si el addon o la clase no existen, detenerse y
resolverlo con el responsable de infraestructura.

## Fase 2: preparar y publicar la imagen

Los siguientes comandos son para **CMD**, desde la raíz del repositorio.
`IMAGE_TAG` usa el SHA completo del commit; la imagen debe existir en ECR antes
de continuar. Si el repositorio ECR no existe, crearlo explícitamente con
`aws ecr create-repository`; no ignorar errores de permisos o conectividad.

```cmd
set AWS_REGION=us-east-1
for /f %i in ('aws sts get-caller-identity --query Account --output text') do set AWS_ACCOUNT_ID=%i
set ECR_REPOSITORY=microservicio-usuarios
set ECR_REGISTRY=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com
for /f %i in ('git rev-parse HEAD') do set IMAGE_TAG=%i
set IMAGE_URI=%ECR_REGISTRY%/%ECR_REPOSITORY%:%IMAGE_TAG%

aws ecr describe-repositories --repository-names %ECR_REPOSITORY% --region %AWS_REGION%
```

Si `describe-repositories` confirma que el repositorio no existe, crearlo:

```cmd
aws ecr create-repository --repository-name %ECR_REPOSITORY% --region %AWS_REGION%
```

Construir, iniciar sesión y publicar:

```cmd
docker build -t microservicio-usuarios:%IMAGE_TAG% .
docker tag microservicio-usuarios:%IMAGE_TAG% %IMAGE_URI%
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_REGISTRY%
docker push %IMAGE_URI%
aws ecr describe-images --repository-name %ECR_REPOSITORY% --image-ids imageTag=%IMAGE_TAG% --region %AWS_REGION%
```

La autenticación pasa por una tubería; no copiar ni imprimir el token de ECR.
No se publica una imagen con etiqueta mutable ni con una imagen de ejemplo.

## Fase 3: preparar Kubernetes

Los comandos de aplicación son intencionalmente individuales. Desde **CMD**,
crear el namespace solo si aún no existe y aplicar la configuración:

```cmd
kubectl get namespace app-pagos >nul 2>&1 || kubectl create namespace app-pagos
kubectl get storageclass gp3 -o yaml
kubectl apply -f k8s/configmap.yaml
```

Aplicar `storageclass-gp3.yaml` únicamente si `gp3` no existe y el responsable
confirma que es la configuración esperada:

```cmd
kubectl apply -f k8s/storageclass-gp3.yaml
```

Si ya existe, comprobar sus parámetros; no reemplazar una clase en uso.

### Crear o actualizar el Secret (PowerShell)

**Cambiar explícitamente de CMD a PowerShell** para este paso. No ejecutar el
manifiesto vacío [secret.yaml](secret.yaml): es solo una plantilla de
referencia. El Secret real `users-secrets` debe contener exactamente
`DATABASE_URL`, `JWT_SECRET_KEY`, `INTERNAL_SERVICE_CREDENTIALS`,
`MARIADB_PASSWORD` y `MARIADB_ROOT_PASSWORD`.

El siguiente ejemplo oculta la captura de credenciales, calcula la huella de
la API Key en memoria y usa un directorio temporal con permisos del usuario
actual para evitar pasar credenciales como argumentos de proceso. Los archivos
temporales se eliminan al terminar; no se imprimen ni se guardan en el
repositorio. PowerShell no reinterpreta `$`, `!`, `\` ni comillas dentro de los
valores capturados. La contraseña se codifica para la URL SQLAlchemy. No
escribir credenciales como literales en el script ni en el historial:

```powershell
function ConvertFrom-SecureInput {
    param([Security.SecureString]$Value)
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$MARIADB_PASSWORD = ConvertFrom-SecureInput (Read-Host -AsSecureString "MariaDB application password")
$MARIADB_ROOT_PASSWORD = ConvertFrom-SecureInput (Read-Host -AsSecureString "MariaDB root password")
$JWT_SECRET_KEY = ConvertFrom-SecureInput (Read-Host -AsSecureString "JWT signing secret")
$apiKey = ConvertFrom-SecureInput (Read-Host -AsSecureString "API Key for pagos-service")

foreach ($value in @($MARIADB_PASSWORD, $MARIADB_ROOT_PASSWORD, $JWT_SECRET_KEY, $apiKey)) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "No se puede crear el Secret: todos los valores son obligatorios."
    }
}

$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    $keyHash = [BitConverter]::ToString(
        $sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($apiKey))
    ).Replace("-", "").ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

$INTERNAL_SERVICE_CREDENTIALS = @{
    "pagos-service" = @{
        key_hashes = @($keyHash)
        permissions = @("users:read_status")
        enabled = $true
    }
} | ConvertTo-Json -Depth 5 -Compress

$encodedPassword = [Uri]::EscapeDataString($MARIADB_PASSWORD)
$DATABASE_URL = "mysql+pymysql://appuser:${encodedPassword}@mariadb:3306/app_pagos_usuarios"

$secretValues = @{
    DATABASE_URL = $DATABASE_URL
    JWT_SECRET_KEY = $JWT_SECRET_KEY
    INTERNAL_SERVICE_CREDENTIALS = $INTERNAL_SERVICE_CREDENTIALS
    MARIADB_PASSWORD = $MARIADB_PASSWORD
    MARIADB_ROOT_PASSWORD = $MARIADB_ROOT_PASSWORD
}
if ($secretValues.Count -ne 5 -or @($secretValues.Values | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -ne 0) {
    throw "El Secret debe contener las cinco claves requeridas con valores no vacíos."
}

$tempDir = Join-Path $env:TEMP ("users-secrets-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    $acl = Get-Acl -Path $tempDir
    $acl.SetAccessRuleProtection($true, $false)
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $rule = New-Object Security.AccessControl.FileSystemAccessRule(
        $identity, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $tempDir -AclObject $acl

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    foreach ($key in $secretValues.Keys) {
        $path = Join-Path $tempDir $key
        [IO.File]::WriteAllText($path, [string]$secretValues[$key], $utf8NoBom)
    }

    $secretArgs = @(
        "create", "secret", "generic", "users-secrets",
        "--namespace=app-pagos",
        "--from-file=DATABASE_URL=$(Join-Path $tempDir 'DATABASE_URL')",
        "--from-file=JWT_SECRET_KEY=$(Join-Path $tempDir 'JWT_SECRET_KEY')",
        "--from-file=INTERNAL_SERVICE_CREDENTIALS=$(Join-Path $tempDir 'INTERNAL_SERVICE_CREDENTIALS')",
        "--from-file=MARIADB_PASSWORD=$(Join-Path $tempDir 'MARIADB_PASSWORD')",
        "--from-file=MARIADB_ROOT_PASSWORD=$(Join-Path $tempDir 'MARIADB_ROOT_PASSWORD')",
        "--dry-run=client", "-o", "yaml"
    )
    $secretManifest = & kubectl @secretArgs
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl no pudo generar users-secrets; no continuar con el despliegue."
    }
    $secretManifest | kubectl apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl no pudo crear o actualizar users-secrets."
    }
}
finally {
    if (Test-Path -LiteralPath $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
    Remove-Variable apiKey, keyHash, secretArgs, secretManifest, secretValues, INTERNAL_SERVICE_CREDENTIALS, DATABASE_URL, encodedPassword, MARIADB_PASSWORD, MARIADB_ROOT_PASSWORD, JWT_SECRET_KEY -ErrorAction SilentlyContinue
}
```

El comando muestra solo el estado de creación/actualización. No continuar si
el bloque anterior falla. Las cinco claves se escriben solo en archivos
temporales protegidos y el bloque los elimina en `finally`, incluso si `kubectl`
falla. Revisar los nombres de claves sin mostrar valores:

```powershell
kubectl describe secret users-secrets -n app-pagos
```

No crear el Secret pasando valores vacíos, no aplicar una plantilla vacía y
nunca guardar credenciales reales en Git. La entrada de ejemplo crea un solo
consumidor; añadir las huellas SHA-256 y permisos reales de cada consumidor
autorizado antes de desplegar.

## Fase 4: desplegar en orden

Continuar desde **CMD** solo cuando la imagen real esté verificada en ECR,
`users-secrets` contenga las cinco claves y el ConfigMap tenga el origen CORS
correcto.

1. Aplicar MariaDB y esperar el StatefulSet y PVC:

   ```cmd
   kubectl apply -f k8s/mariadb.yaml
   kubectl wait --for=jsonpath={.status.phase}=Bound pvc/mariadb-data-mariadb-0 -n app-pagos --timeout=10m
   kubectl rollout status statefulset/mariadb -n app-pagos --timeout=10m
   ```

2. Generar localmente el manifiesto FastAPI con la imagen ECR publicada. Abrir
   **PowerShell**; `fastapi.rendered.yaml` está ignorado por Git y no contiene
   credenciales:

   ```powershell
   $AWS_REGION = "us-east-1"
   $AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text).Trim()
   $IMAGE_TAG = (git rev-parse HEAD).Trim()
   if ($LASTEXITCODE -ne 0 -or $IMAGE_TAG -notmatch '^[0-9a-f]{40}$') {
       throw "Se requiere un SHA completo de commit para etiquetar la imagen."
   }
   $ECR_IMAGE_URI = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/microservicio-usuarios:${IMAGE_TAG}"
   if ($ECR_IMAGE_URI -notmatch '^\d{12}\.dkr\.ecr\.us-east-1\.amazonaws\.com/microservicio-usuarios:[0-9a-f]{40}$') {
       throw "La imagen debe ser una URI de ECR de us-east-1 etiquetada con el SHA."
   }
   aws ecr describe-images --repository-name microservicio-usuarios --image-ids "imageTag=$IMAGE_TAG" --region $AWS_REGION
   if ($LASTEXITCODE -ne 0) {
       throw "La imagen no está publicada en ECR; no generar ni aplicar el Deployment."
   }

   $template = Get-Content k8s\fastapi.yaml -Raw
   $placeholder = "REPLACE_WITH_ECR_IMAGE_URI"
   if (-not $template.Contains($placeholder)) {
       throw "No se encontró el marcador de imagen esperado en la plantilla."
   }
   $rendered = $template.Replace($placeholder, $ECR_IMAGE_URI)
   if ($rendered.Contains($placeholder)) {
       throw "La imagen conserva el marcador placeholder; no aplicar."
   }
   Set-Content -Path k8s\fastapi.rendered.yaml -Value $rendered -Encoding utf8
   ```

   Volver a **CMD** y aplicar únicamente el archivo renderizado:

   ```cmd
   findstr /C:"REPLACE_WITH_ECR_IMAGE_URI" k8s\fastapi.rendered.yaml
   ```

   Si `findstr` encuentra el marcador, detenerse. Si no lo encuentra:

   ```cmd
   kubectl apply -f k8s\fastapi.rendered.yaml
   kubectl rollout status deployment/users-api -n app-pagos --timeout=10m
   ```

3. Aplicar Nginx y esperar al gateway:

   ```cmd
   kubectl apply -f k8s/nginx.yaml
   kubectl rollout status deployment/users-gateway -n app-pagos --timeout=10m
   ```

4. Verificar los recursos y disponibilidad:

   ```cmd
   kubectl get pods,services,pvc -n app-pagos
   kubectl get services -n app-pagos -o wide
   kubectl get endpoints -n app-pagos
   kubectl describe secret users-secrets -n app-pagos
   ```

   Confirmar pods `Ready`, PVC `Bound`, y que los Services continúan siendo
   `ClusterIP`. El DNS interno de FastAPI es
   `http://users-api.app-pagos.svc.cluster.local:8000`.

Al finalizar, eliminar solo el archivo local renderizado:

```powershell
Remove-Item k8s\fastapi.rendered.yaml
```

## Persistencia y escalado

El PVC creado por `volumeClaimTemplates` puede permanecer después de eliminar
el StatefulSet. El StorageClass `gp3` usa cifrado EBS y `reclaimPolicy: Delete`,
pero la eliminación del clúster no garantiza que desaparezcan todos los
recursos AWS. Verificar volúmenes EBS y otros recursos residuales con el
responsable de infraestructura.

Mantener una réplica de FastAPI mientras `FAILED_LOGINS` siga en memoria. Antes
de escalar, migrar el contador a almacenamiento compartido y persistente.

Los consumidores internos usan API Keys por `X-API-Key` y llaman directamente
al DNS de `users-api`; Nginx devuelve 404 para `/internal` y `/internal/`.
