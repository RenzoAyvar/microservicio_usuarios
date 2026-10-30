from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app_pagos_usuarios.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_HOURS", "3")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


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
