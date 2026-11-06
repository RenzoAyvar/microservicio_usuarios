from __future__ import annotations

import re
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings, validate_settings
from app.database import SessionLocal, Base, engine, get_db
from app.deps import get_current_user, require_service_permission, _load_internal_consumers
from app.models import Role, Usuario
from app.schemas import InternalUserStatus, LoginRequest, MessageResponse, TokenResponse, UserCreate, UserPublic, UserUpdate
from app.security import clear_failed_attempts, create_access_token, hash_password, is_account_locked, register_failed_attempt, verify_password

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def password_is_valid(password: str) -> bool:
    if not 8 <= len(password) <= 16:
        return False
    if not any(character.isupper() for character in password):
        return False
    if not any(character.islower() for character in password):
        return False
    if not any(character.isdigit() for character in password):
        return False
    return True


def ensure_default_roles(db: Session) -> None:
    roles = {
        "usuario": "Usuario común",
        "administrador": "Administrador",
    }
    for nombre, descripcion in roles.items():
        role = db.query(Role).filter(Role.nombre == nombre).first()
        if role is None:
            db.add(Role(nombre=nombre, descripcion=descripcion))
    db.commit()


def serialize_user(user: Usuario) -> dict:
    return {
        "id_usuario": user.id_usuario,
        "nombre": user.nombre,
        "apellido": user.apellido,
        "email": user.email,
        "estado": user.estado,
        "fecha_registro": user.fecha_registro,
        "fecha_actualizacion": user.fecha_actualizacion,
        "ultimo_acceso": user.ultimo_acceso,
        "id_rol": user.id_rol,
        "telefono": user.telefono,
        "direccion": user.direccion,
        "fecha_nacimiento": user.fecha_nacimiento,
        "rol": user.rol.nombre if user.rol else "usuario",
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings()
    _load_internal_consumers()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_roles(db)
    finally:
        db.close()
    yield


app.router.lifespan_context = lifespan


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/live")
def liveness() -> dict:
    return {"status": "alive"}


@app.get("/api/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Base de datos no disponible") from exc
    return {"status": "ready"}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserPublic)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)) -> dict:
    if not password_is_valid(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener entre 8 y 16 caracteres, una mayúscula, una minúscula y un número.",
        )

    normalized_email = user_data.email.lower().strip()
    existing = db.query(Usuario).filter(Usuario.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Correo ya registrado")

    default_role = db.query(Role).filter(Role.nombre == "usuario").first()
    if default_role is None:
        ensure_default_roles(db)
        default_role = db.query(Role).filter(Role.nombre == "usuario").first()

    new_user = Usuario(
        nombre=user_data.nombre.strip(),
        apellido=user_data.apellido.strip(),
        email=normalized_email,
        password_hash=hash_password(user_data.password),
        estado=True,
        fecha_registro=datetime.utcnow(),
        id_rol=default_role.id_rol,
        telefono=user_data.telefono.strip(),
        direccion=user_data.direccion.strip() if user_data.direccion else None,
        fecha_nacimiento=user_data.fecha_nacimiento,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    new_user.rol = default_role
    return serialize_user(new_user)


@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(login_data: LoginRequest, db: Session = Depends(get_db)) -> dict:
    normalized_email = login_data.email.lower().strip()
    if is_account_locked(normalized_email):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    user = db.query(Usuario).filter(Usuario.email == normalized_email).first()
    if user is None or not user.estado or not verify_password(login_data.password, user.password_hash):
        register_failed_attempt(normalized_email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    clear_failed_attempts(normalized_email)
    user.ultimo_acceso = datetime.utcnow()
    db.add(user)
    db.commit()
    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/users/me", response_model=UserPublic)
def get_current_user_profile(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    current_user.rol = db.query(Role).filter(Role.id_rol == current_user.id_rol).first()
    return serialize_user(current_user)


@app.put("/api/users/me", response_model=UserPublic)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user_update.nombre is not None:
        current_user.nombre = user_update.nombre.strip()
    if user_update.apellido is not None:
        current_user.apellido = user_update.apellido.strip()
    if user_update.telefono is not None:
        current_user.telefono = user_update.telefono.strip()
    if user_update.direccion is not None:
        current_user.direccion = user_update.direccion.strip() or None
    if user_update.fecha_nacimiento is not None:
        current_user.fecha_nacimiento = user_update.fecha_nacimiento
    if user_update.email is not None:
        new_email = str(user_update.email).lower().strip()
        if new_email != current_user.email:
            existing_user = db.query(Usuario).filter(Usuario.email == new_email).first()
            if existing_user and existing_user.id_usuario != current_user.id_usuario:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Correo ya registrado")
            current_user.email = new_email
            clear_failed_attempts(new_email)

    current_user.fecha_actualizacion = datetime.utcnow()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    current_user.rol = db.query(Role).filter(Role.id_rol == current_user.id_rol).first()
    return serialize_user(current_user)


@app.get("/internal/users/{id_usuario}", response_model=InternalUserStatus)
def get_internal_user_status(
    id_usuario: int,
    consumer_id: str = Depends(require_service_permission("users:read_status")),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {"id_usuario": user.id_usuario, "estado": bool(user.estado)}
