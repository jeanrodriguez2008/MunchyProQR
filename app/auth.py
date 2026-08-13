import os
from datetime import datetime, timedelta
from typing import Optional

# Parche de compatibilidad entre passlib y bcrypt 4.0+
import bcrypt
if not hasattr(bcrypt, "__about__"):
    class About:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")
    bcrypt.__about__ = About()

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "munchyproqr_secret_key_super_segura_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    # Trunca automáticamente a 72 bytes para prevenir excepciones de bcrypt
    plain_password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(plain_password_bytes, hashed_password)

def obtener_password_hash(password: str) -> str:
    # Trunca automáticamente a 72 bytes para prevenir excepciones de bcrypt
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes)

def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    a_copiar = data.copy()
    if expires_delta:
        expiracion = datetime.utcnow() + expires_delta
    else:
        expiracion = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    a_copiar.update({"exp": expiracion})
    token_jwt = jwt.encode(a_copiar, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt

def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Usuario:
    excepcion_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise excepcion_credenciales
    except JWTError:
        raise excepcion_credenciales

    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None:
        raise excepcion_credenciales
        
    return usuario

def requiere_webmaster(
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
) -> Usuario:
    if usuario_actual.rol.lower() != "webmaster":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido al Webmaster"
        )
    return usuario_actual

def requiere_coordinador(
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
) -> Usuario:
    if usuario_actual.rol.lower() not in ["coordinador", "webmaster"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de Coordinador o Webmaster"
        )
    return usuario_actual

def requiere_analista_o_coordinador(
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
) -> Usuario:
    if usuario_actual.rol.lower() not in ["analista", "coordinador", "webmaster"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol no autorizado dentro del sistema"
        )
    return usuario_actual