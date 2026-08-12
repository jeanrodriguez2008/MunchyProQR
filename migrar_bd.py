from sqlalchemy import text
from app.database import engine

def actualizar_base_datos():
    print("Expandiendo columnas en Neon Tech para evitar errores de almacenamiento...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS codigo_articulo VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS descripcion TEXT;"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS fecha_vencimiento VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS num_recibo VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS turno VARCHAR(50);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS grupo VARCHAR(50);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS fecha_recibo VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS fecha_contabilizacion VARCHAR(100);"))
        conn.execute(text("ALTER TABLE salidas_produccion ADD COLUMN IF NOT EXISTS num_op VARCHAR(100);"))
        conn.commit()
        print(" -> Base de datos actualizada y protegida contra textos largos.")

if __name__ == "__main__":
    actualizar_base_datos()