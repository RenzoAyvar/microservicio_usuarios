from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: str = Field(..., min_length=7, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=150)
    fecha_nacimiento: date


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=16)


class UserUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(default=None, min_length=7, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=150)
    fecha_nacimiento: Optional[date] = None

    model_config = ConfigDict(extra="forbid")


class UserPublic(BaseModel):
    id_usuario: int
    nombre: str
    apellido: str
    email: EmailStr
    estado: bool
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    ultimo_acceso: Optional[datetime] = None
    id_rol: int
    telefono: str
    direccion: Optional[str] = None
    fecha_nacimiento: date
    rol: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
