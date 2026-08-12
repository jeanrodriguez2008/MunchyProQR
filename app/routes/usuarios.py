from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(
    prefix="/api/usuarios",
    tags=["Gestión de Usuarios"]
)

@router.get("/", response_model=List[schemas.UsuarioResponse])
def listar_todos_los_usuarios(
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(auth.requiere_webmaster)
):
    # Retorna la lista completa de usuarios para el panel del webmaster
    return db.query(models.Usuario).order_by(models.Usuario.id.asc()).all()


@router.put("/{usuario_id}/rol")
def cambiar_rol_usuario(
    usuario_id: int,
    nuevo_rol: str,
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(auth.requiere_webmaster)
):
    if nuevo_rol.lower() not in ["analista", "coordinador", "webmaster"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol no válido. Debe ser 'analista', 'coordinador' o 'webmaster'."
        )

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    usuario.rol = nuevo_rol.lower()
    db.commit()
    db.refresh(usuario)
    return {"mensaje": f"Rol actualizado a '{nuevo_rol}' para el usuario {usuario.username}"}