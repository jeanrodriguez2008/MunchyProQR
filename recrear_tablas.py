from sqlalchemy import text
from app.database import engine
from app.models import Base

def reset_tabla_salidas():
    print("Reconstruyendo la tabla 'salidas_produccion' en Neon Tech...")
    with engine.connect() as conn:
        # 1. Eliminar la tabla anterior con estructura desactualizada
        conn.execute(text("DROP TABLE IF EXISTS salidas_produccion CASCADE;"))
        conn.commit()
        print(" -> Tabla antigua eliminada.")
        
    # 2. Crear la tabla con todas las 12 columnas oficiales
    Base.metadata.create_all(bind=engine)
    print(" -> Nueva tabla 'salidas_produccion' creada con éxito con todas sus columnas.")

if __name__ == "__main__":
    reset_tabla_salidas()