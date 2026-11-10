
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

# Solicitar credenciales sin mostrarlas en pantalla
$MARIADB_PASSWORD = ConvertFrom-SecureInput (Read-Host -AsSecureString "MariaDB application password")
$MARIADB_ROOT_PASSWORD = ConvertFrom-SecureInput (Read-Host -AsSecureString "MariaDB root password")
$JWT_SECRET_KEY = ConvertFrom-SecureInput (Read-Host -AsSecureString "JWT signing secret")
$apiKey = ConvertFrom-SecureInput (Read-Host -AsSecureString "API Key for pagos-service")

# Validar que no existan valores vacíos
foreach ($value in @($MARIADB_PASSWORD, $MARIADB_ROOT_PASSWORD, $JWT_SECRET_KEY, $apiKey)) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Todos los valores son obligatorios."
    }
}

# Generar SHA-256 de la API Key
$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    $keyHash = [BitConverter]::ToString(
        $sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($apiKey))
    ).Replace("-", "").ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

# Configurar consumidor interno
$INTERNAL_SERVICE_CREDENTIALS = @{
    "pagos-service" = @{
        key_hashes = @($keyHash)
        permissions = @("users:read_status")
        enabled = $true
    }
} | ConvertTo-Json -Depth 5 -Compress

# Construir conexión a MariaDB
$encodedPassword = [Uri]::EscapeDataString($MARIADB_PASSWORD)
$DATABASE_URL = "mysql+pymysql://appuser:${encodedPassword}@mariadb:3306/app_pagos_usuarios"

# Preparar las cinco claves
$secretValues = @{
    DATABASE_URL = $DATABASE_URL
    JWT_SECRET_KEY = $JWT_SECRET_KEY
    INTERNAL_SERVICE_CREDENTIALS = $INTERNAL_SERVICE_CREDENTIALS
    MARIADB_PASSWORD = $MARIADB_PASSWORD
    MARIADB_ROOT_PASSWORD = $MARIADB_ROOT_PASSWORD
}

if ($secretValues.Count -ne 5 -or @($secretValues.Values | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -ne 0) {
    throw "El Secret debe contener cinco valores no vacíos."
}

# Crear directorio temporal protegido
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

    # Crear el manifiesto sin mostrar las credenciales
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
        throw "No se pudo generar el Secret."
    }

    $secretManifest | kubectl apply -f -

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo aplicar el Secret."
    }

    Write-Host "Proceso de creación del Secret finalizado."
}
finally {
    if (Test-Path -LiteralPath $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }

    Remove-Variable apiKey, keyHash, secretArgs, secretManifest, secretValues, INTERNAL_SERVICE_CREDENTIALS, DATABASE_URL, encodedPassword, MARIADB_PASSWORD, MARIADB_ROOT_PASSWORD, JWT_SECRET_KEY -ErrorAction SilentlyContinue
}
