# Microservicio de Usuarios

Backend FastAPI para la gestión de usuarios de la aplicación de pagos, conforme a la especificación `Spec_Usuarios.md`.

## Requisitos

- Python 3.13+
- MariaDB 11.8.9 (o base de datos compatible con SQLAlchemy)
- Docker y Docker Compose (opcional)

## Configuración

1. Copia `.env.example` a `.env` y ajusta los valores.
2. Crea la base de datos `app_pagos_usuarios` en MariaDB.
3. Instala dependencias:

```bash
python -m pip install -r requirements.txt
```

## Ejecutar localmente

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La documentación interactiva queda en:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Endpoints principales

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`
- `PUT /api/users/me`
- `GET /api/health`

## Pruebas

```bash
pytest -q tests/test_user_service.py
```

## Arquitectura

- FastAPI para la API REST
- SQLAlchemy + MariaDB para persistencia
- JWT para autenticación
- Argon2id para hashing de contraseñas
- Nginx como gateway de entrada
