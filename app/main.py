import os
from pathlib import Path
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, Base, get_db
from app import models, schemas, auth
from app.routes import salidas

# 1. Función para migrar la base de datos agregando todas las columnas faltantes
def migrar_base_de_datos():
    with engine.connect() as conn:
        try:
            # Migraciones para la tabla de Usuarios
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS pregunta_secreta VARCHAR;"))
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS respuesta_secreta_hash VARCHAR;"))
            
            # Migraciones indispensables para la Conciliación de Almacén en Salidas
            conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS recibido_almacen BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS fecha_hora_recepcion TIMESTAMP WITHOUT TIME ZONE;"))
            conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS usuario_recepcion_id INTEGER REFERENCES usuarios(id);"))
            
            conn.commit()
            print(" -> Migración de BD completada: Todas las columnas de Almacén y Usuarios verificadas/agregadas.")
        except Exception as e:
            print(f" -> Aviso migración BD: {e}")

# Ejecutar migración y creación de tablas
migrar_base_de_datos()
models.Base.metadata.create_all(bind=engine)

# 2. Inicializar la aplicación FastAPI
app = FastAPI(title="MunchyProQR API", version="1.0.0")

# 3. Montar carpeta estática
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 4. Incluir routers de producción
app.include_router(salidas.router)


def respuesta_html_sin_cache(nombre_archivo: str) -> FileResponse:
    ruta_archivo = Path(__file__).resolve().parent / "templates" / nombre_archivo
    response = FileResponse(ruta_archivo)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.on_event("startup")
def crear_usuarios_iniciales():
    db = next(get_db())
    webmaster_existente = db.query(models.Usuario).filter(models.Usuario.rol == "webmaster").first()
    
    if not webmaster_existente:
        webmaster_defecto = models.Usuario(
            username="webmaster",
            email="webmaster@munchy.com",
            nombre_completo="Webmaster Administrador",
            rol="webmaster",
            password_hash=auth.obtener_password_hash("Webmaster2026*"),
            pregunta_secreta="¿Empresa?",
            respuesta_secreta_hash=auth.obtener_password_hash("munchy")
        )
        db.add(webmaster_defecto)
        db.commit()
        print(" -> Webmaster por defecto creado: Usuario='webmaster', Clave='Webmaster2026*'")


# --- Vistas HTML Protegidas por Rol ---
@app.get("/")
def vista_login():
    return respuesta_html_sin_cache("index.html")

# Accesible por Analista, Almacenista, Coordinador y Webmaster
@app.get("/scanner-view")
def vista_escanner():
    return respuesta_html_sin_cache("scanner.html")

# Accesible por Consultor, Coordinador y Webmaster
@app.get("/dashboard-view")
def vista_dashboard():
    return respuesta_html_sin_cache("dashboard.html")

# Exclusivo para Webmaster
@app.get("/webmaster-view")
def vista_webmaster():
    return respuesta_html_sin_cache("webmaster.html")


# --- Autenticación ---
@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    
    if not usuario or not auth.verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.crear_token_acceso(
        data={"sub": usuario.username, "rol": usuario.rol}
    )
    
    return {"access_token": access_token, "token_type": "bearer", "rol": usuario.rol}


# --- Registro Público de Usuarios (Se crean como analista por defecto) ---
@app.post("/registro-publico", response_model=schemas.UsuarioResponse)
def registro_publico(
    usuario: schemas.UsuarioCreate, 
    db: Session = Depends(get_db)
):
    if db.query(models.Usuario).filter(models.Usuario.username == usuario.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    if db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    nuevo_usuario = models.Usuario(
        username=usuario.username.strip().lower(),
        email=usuario.email.strip().lower(),
        nombre_completo=usuario.nombre_completo,
        rol="analista",
        password_hash=auth.obtener_password_hash(usuario.password),
        pregunta_secreta=usuario.pregunta_secreta.strip(),
        respuesta_secreta_hash=auth.obtener_password_hash(usuario.respuesta_secreta.strip().lower())
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# --- Obtener Pregunta Secreta ---
@app.get("/api/usuarios/pregunta-secreta/{username}")
def obtener_pregunta_secreta(username: str, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == username.strip().lower()).first()
    if not user or not user.pregunta_secreta:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin pregunta configurada")
    return {"pregunta_secreta": user.pregunta_secreta}


# --- Recuperar Contraseña ---
@app.post("/api/usuarios/recuperar-clave")
def recuperar_clave(data: schemas.RecuperarClaveRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == data.username.strip().lower()).first()
    if not user or not user.respuesta_secreta_hash:
        raise HTTPException(status_code=400, detail="No se pudo procesar la solicitud")

    if not auth.verificar_password(data.respuesta_secreta.strip().lower(), user.respuesta_secreta_hash):
        raise HTTPException(status_code=400, detail="La respuesta secreta es incorrecta")

    user.password_hash = auth.obtener_password_hash(data.nueva_password)
    db.commit()
    return {"mensaje": "Contraseña actualizada exitosamente"}


# --- Endpoints Exclusivos para Webmaster ---
@app.get("/api/usuarios")
def listar_todos_usuarios(
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(auth.requiere_webmaster)
):
    usuarios = db.query(models.Usuario).order_by(models.Usuario.id.asc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "nombre_completo": u.nombre_completo,
            "rol": u.rol
        }
        for u in usuarios
    ]


@app.put("/api/usuarios/{usuario_id}/rol")
def cambiar_rol_usuario(
    usuario_id: int,
    nuevo_rol: str,
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(auth.requiere_webmaster)
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.rol = nuevo_rol.lower()
    db.commit()
    return {"mensaje": f"Rol actualizado a {nuevo_rol}"}


# --- Cambio Directo de Contraseña por el Webmaster ---
@app.put("/api/usuarios/{usuario_id}/cambiar-clave")
def cambiar_clave_usuario(
    usuario_id: int,
    nueva_clave: str,
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(auth.requiere_webmaster)
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if len(nueva_clave.strip()) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres")

    user.password_hash = auth.obtener_password_hash(nueva_clave.strip())
    db.commit()
    return {"mensaje": f"Contraseña del usuario '{user.username}' actualizada exitosamente"}


# --- Eliminar Usuario Protegiendo al Webmaster ---
@app.delete("/api/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(auth.requiere_webmaster)
):
    user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user.rol.lower() == "webmaster":
        raise HTTPException(status_code=400, detail="El usuario Webmaster está protegido y no puede ser eliminado.")

    db.delete(user)
    db.commit()
    return None