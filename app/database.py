import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno desde el archivo .env en local (si existe)
load_dotenv()

# Leer la variable de entorno desde Render o desde el .env local
DATABASE_URL = os.getenv("DATABASE_URL")

# Si no hay variable configurada, se detiene con una alerta clara
if not DATABASE_URL or "tu_usuario_real" in DATABASE_URL or "usuario:password" in DATABASE_URL:
    raise ValueError(
        "ERROR CRÍTICO DE CONFIGURACIÓN: No se encontró la variable DATABASE_URL válida. "
        "Configura la cadena de conexión de Neon Tech en las variables de entorno de Render "
        "o dentro del archivo .env en tu entorno local."
    )

# Compatibilidad para SQLAlchemy si la URI empieza por postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Crear motor de conexión optimizado para Neon Tech (PostgreSQL)
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    pool_recycle=300
)

# Generador de sesiones para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para la estructura de modelos
Base = declarative_base()

# Dependencia para inyectar la sesión BD en las rutas de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()