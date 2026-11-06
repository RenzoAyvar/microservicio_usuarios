from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Iterable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi import Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Usuario
from app.security import decode_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")

    email = decode_access_token(credentials.credentials)
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    if not user.estado:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    return user


def api_key_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _load_internal_consumers() -> dict[str, dict[str, Any]]:
    try:
        consumers = json.loads(settings.internal_service_credentials)
    except json.JSONDecodeError as exc:
        raise RuntimeError("INTERNAL_SERVICE_CREDENTIALS debe contener JSON valido") from exc

    if not isinstance(consumers, dict):
        raise RuntimeError("INTERNAL_SERVICE_CREDENTIALS debe contener un objeto JSON")
    validate_internal_consumers(consumers)
    return consumers


def validate_internal_consumers(consumers: dict[str, dict[str, Any]]) -> None:
    seen_fingerprints: set[str] = set()
    allowed_permissions = {"users:read_status"}

    for consumer_id, consumer in consumers.items():
        if not isinstance(consumer_id, str) or not consumer_id.strip():
            raise RuntimeError("El identificador de consumidor interno no puede estar vacio")
        if not isinstance(consumer, dict):
            raise RuntimeError(f"La configuracion de {consumer_id} debe ser un objeto JSON")

        key_hashes = consumer.get("key_hashes")
        permissions = consumer.get("permissions")
        enabled = consumer.get("enabled")
        if not isinstance(key_hashes, list) or not key_hashes:
            raise RuntimeError(f"{consumer_id} debe tener al menos una huella de API Key")
        if not isinstance(permissions, list):
            raise RuntimeError(f"{consumer_id} debe contener una lista de permisos")
        if not isinstance(enabled, bool):
            raise RuntimeError(f"{consumer_id} debe definir enabled como booleano")

        unknown_permissions = set(permissions) - allowed_permissions
        if unknown_permissions:
            raise RuntimeError(f"{consumer_id} contiene permisos internos desconocidos")

        for key_hash in key_hashes:
            if (
                not isinstance(key_hash, str)
                or len(key_hash) != 64
                or any(character not in "0123456789abcdef" for character in key_hash.lower())
            ):
                raise RuntimeError(f"{consumer_id} contiene una huella de API Key invalida")
            normalized = key_hash.lower()
            if normalized in seen_fingerprints:
                raise RuntimeError("Hay huellas de API Key duplicadas en la configuracion interna")
            seen_fingerprints.add(normalized)


def _secure_fingerprint_matches(api_key: str, configured_fingerprints: Iterable[str]) -> bool:
    incoming = api_key_fingerprint(api_key)
    matched = False
    for configured in configured_fingerprints:
        matched = hmac.compare_digest(incoming, configured.lower()) or matched
    return matched


def require_service_permission(permission: str):
    def dependency(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
        if not x_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales de servicio invalidas")

        consumers = _load_internal_consumers()
        consumer_id = ""
        permissions: set[str] = set()
        matched = False

        for candidate_id, candidate in consumers.items():
            if not isinstance(candidate, dict) or not candidate.get("enabled", False):
                continue
            key_hashes = candidate.get("key_hashes", [])
            if not isinstance(key_hashes, list):
                continue
            candidate_matched = _secure_fingerprint_matches(x_api_key, key_hashes)
            if candidate_matched:
                consumer_id = candidate_id
                candidate_permissions = candidate.get("permissions", [])
                if isinstance(candidate_permissions, list):
                    permissions = set(candidate_permissions)
                matched = True

        if not matched:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales de servicio invalidas")
        if permission not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso insuficiente")
        return consumer_id

    return dependency
