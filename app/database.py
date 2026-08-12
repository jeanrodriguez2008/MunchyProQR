import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno desde el archivo .env ubicado en la raíz
load_dotenv()

# Leer la variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

# Si la variable no existe o conserva el texto de plantilla, detiene con un mensaje claro
if not DATABASE_URL or "tu_usuario_real" in DATABASE_URL or "usuario:password" in DATABASE_URL:
    raise ValueError(
        "ERROR DE CONFIGURACIÓN: Debes colocar tu cadena de conexión REAL de Neon Tech "
        "dentro del archivo .env en la raíz del proyecto."
    )

# Compatibilidad de prefijo para SQLAlchemy si viene como postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Crear motor de conexión con Neon Tech
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Generador de sesiones para las consultas
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para modelos
Base = declarative_base()

# Dependencia para las rutas de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()