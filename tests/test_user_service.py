from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_app_pagos_usuarios.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_HOURS"] = "3"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["INTERNAL_SERVICE_CREDENTIALS"] = '{"pagos-service":{"key_hashes":["test-key-hash"],"permissions":["users:read_status"],"enabled":true}}'

from app.deps import api_key_fingerprint
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Usuario
from app.config import Settings, validate_settings

client = TestClient(app, raise_server_exceptions=False)


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def set_service_credentials() -> None:
    from app.config import settings
    settings.internal_service_credentials = (
        '{"pagos-service":{"key_hashes":["%s"],"permissions":["users:read_status"],"enabled":true},'
        '"reportes-service":{"key_hashes":["%s"],"permissions":[],"enabled":true},'
        '"deshabilitado-service":{"key_hashes":["%s"],"permissions":["users:read_status"],"enabled":false}}'
        % (
            api_key_fingerprint("pagos-api-key"),
            api_key_fingerprint("reportes-api-key"),
            api_key_fingerprint("deshabilitado-api-key"),
        )
    )


def test_register_login_and_profile_flow() -> None:
    reset_db()
    payload = {
        "nombre": "Ana",
        "apellido": "García",
        "email": "ana@example.com",
        "password": "ClaveSegura1",
        "telefono": "5551234567",
        "direccion": "Calle 123",
        "fecha_nacimiento": "1995-05-12",
    }

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    user = response.json()
    assert user["email"] == "ana@example.com"
    assert "password_hash" not in response.text.lower()

    login_response = client.post(
        "/api/auth/login",
        json={"email": "ana@example.com", "password": "ClaveSegura1"},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    assert token

    profile_response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["email"] == "ana@example.com"

    update_response = client.put(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"telefono": "5550001111", "direccion": "Avenida Siempre Viva 742"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["telefono"] == "5550001111"


def test_duplicate_email_is_rejected() -> None:
    reset_db()
    payload = {
        "nombre": "Luis",
        "apellido": "Torres",
        "email": "luis@example.com",
        "password": "ClaveSegura1",
        "telefono": "5551234567",
        "fecha_nacimiento": "1990-01-01",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/auth/register", json={**payload, "nombre": "Pedro"})
    assert second.status_code == 409


def test_invalid_password_is_rejected() -> None:
    reset_db()
    response = client.post(
        "/api/auth/register",
        json={
            "nombre": "Maria",
            "apellido": "Lopez",
            "email": "maria@example.com",
            "password": "clavesegura",
            "telefono": "5555555555",
            "fecha_nacimiento": "1992-02-02",
        },
    )
    assert response.status_code == 400


def test_login_lockout_after_three_failures() -> None:
    reset_db()
    payload = {
        "nombre": "Javier",
        "apellido": "Rojas",
        "email": "javier@example.com",
        "password": "ClaveSegura1",
        "telefono": "5557777777",
        "fecha_nacimiento": "1988-08-08",
    }
    registration = client.post("/api/auth/register", json=payload)
    assert registration.status_code == 201

    for _ in range(3):
        failed = client.post(
            "/api/auth/login",
            json={"email": payload["email"], "password": "WrongPassword1"},
        )
        assert failed.status_code == 401

    locked = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "ClaveSegura1"},
    )
    assert locked.status_code == 401
    assert "Credenciales incorrectas" in locked.json()["detail"]


def test_internal_user_status() -> None:
    reset_db()
    set_service_credentials()
    payload = {
        "nombre": "Lucia",
        "apellido": "Perez",
        "email": "lucia@example.com",
        "password": "ClaveSegura1",
        "telefono": "5551112222",
        "fecha_nacimiento": "1993-03-03",
    }
    registration = client.post("/api/auth/register", json=payload)
    user_id = registration.json()["id_usuario"]

    response = client.get(
        f"/internal/users/{user_id}",
        headers={"X-API-Key": "pagos-api-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"id_usuario": user_id, "estado": True}


def test_internal_endpoint_requires_api_key_and_permission() -> None:
    reset_db()
    set_service_credentials()

    missing = client.get("/internal/users/999")
    assert missing.status_code == 401

    invalid = client.get(
        "/internal/users/999",
        headers={"X-API-Key": "api-key-invalida"},
    )
    assert invalid.status_code == 401

    forbidden = client.get(
        "/internal/users/999",
        headers={"X-API-Key": "reportes-api-key"},
    )
    assert forbidden.status_code == 403


def test_internal_endpoint_rejects_disabled_consumer() -> None:
    reset_db()
    set_service_credentials()

    response = client.get(
        "/internal/users/999",
        headers={"X-API-Key": "deshabilitado-api-key"},
    )

    assert response.status_code == 403


def test_internal_endpoint_hides_personal_data() -> None:
    reset_db()
    set_service_credentials()
    payload = {
        "nombre": "Privada",
        "apellido": "Persona",
        "email": "privada@example.com",
        "password": "ClaveSegura1",
        "telefono": "5559998888",
        "fecha_nacimiento": "1990-01-01",
    }
    registration = client.post("/api/auth/register", json=payload)
    user_id = registration.json()["id_usuario"]

    response = client.get(
        f"/internal/users/{user_id}",
        headers={"X-API-Key": "pagos-api-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"id_usuario": user_id, "estado": True}
    assert "email" not in response.text
    assert "nombre" not in response.text
    assert "telefono" not in response.text


def test_internal_user_status_distinguishes_inactive_and_missing() -> None:
    reset_db()
    set_service_credentials()
    payload = {
        "nombre": "Sofia",
        "apellido": "Diaz",
        "email": "sofia@example.com",
        "password": "ClaveSegura1",
        "telefono": "5553334444",
        "fecha_nacimiento": "1991-01-01",
    }
    registration = client.post("/api/auth/register", json=payload)
    user_id = registration.json()["id_usuario"]

    db = SessionLocal()
    db_user = db.query(Usuario).filter(Usuario.id_usuario == user_id).first()
    db_user.estado = False
    db.commit()
    db.close()

    inactive = client.get(
        f"/internal/users/{user_id}",
        headers={"X-API-Key": "pagos-api-key"},
    )
    assert inactive.status_code == 200
    assert inactive.json() == {"id_usuario": user_id, "estado": False}

    missing = client.get(
        "/internal/users/999999",
        headers={"X-API-Key": "pagos-api-key"},
    )
    assert missing.status_code == 404


def test_nginx_blocks_external_internal_routes() -> None:
    nginx_config = Path("nginx.conf").read_text(encoding="utf-8")

    assert "location ^~ /internal/" in nginx_config
    assert "return 404;" in nginx_config


def test_fastapi_lifespan_starts_and_stops() -> None:
    with TestClient(app) as lifecycle_client:
        response = lifecycle_client.get("/api/live")
    assert response.status_code == 200


def test_production_rejects_sqlite() -> None:
    candidate = Settings(
        _env_file=None,
        database_url="sqlite:///./insecure.db",
        jwt_secret_key="secure-test-secret",
        internal_service_credentials='{"pagos":{"key_hashes":["0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"],"permissions":["users:read_status"],"enabled":true}}',
        app_env="production",
    )
    try:
        validate_settings(candidate)
        assert False, "La configuración debería rechazarse"
    except RuntimeError as exc:
        assert "SQLite" in str(exc)


def test_production_rejects_default_jwt_secret() -> None:
    candidate = Settings(
        _env_file=None,
        database_url="mysql+pymysql://app:secret@mariadb:3306/app_pagos_usuarios",
        jwt_secret_key="change-this-secret-key",
        internal_service_credentials='{"pagos":{"key_hashes":["0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"],"permissions":["users:read_status"],"enabled":true}}',
        app_env="production",
    )
    try:
        validate_settings(candidate)
        assert False, "La configuración debería rechazarse"
    except RuntimeError as exc:
        assert "JWT_SECRET_KEY" in str(exc)
