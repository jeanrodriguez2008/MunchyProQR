from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    nombre_completo: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    password: str
    pregunta_secreta: str
    respuesta_secreta: str

class UsuarioResponse(UsuarioBase):
    id: int
    rol: str

    class Config:
        from_attributes = True

class RecuperarClaveRequest(BaseModel):
    username: str
    respuesta_secreta: str
    nueva_password: str

class SalidaBase(BaseModel):
    codigo_qr: str
    codigo_articulo: Optional[str] = None
    descripcion: str
    lote: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    cantidad: int = 1
    num_recibo: Optional[str] = None
    turno: Optional[str] = None
    grupo: Optional[str] = None
    fecha_recibo: Optional[str] = None
    fecha_contabilizacion: Optional[str] = None
    num_op: Optional[str] = None

class SalidaCreate(SalidaBase):
    pass

class SalidaResponse(SalidaBase):
    id: int
    fecha_hora: datetime
    usuario_id: int

    class Config:
        from_attributes = True