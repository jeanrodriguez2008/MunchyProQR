from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre_completo = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    rol = Column(String, default="analista") # analista, coordinador, webmaster
    
    # Recuperación de clave
    pregunta_secreta = Column(String, nullable=True)
    respuesta_secreta_hash = Column(String, nullable=True)

    salidas = relationship("SalidaProduccion", back_populates="usuario")


class SalidaProduccion(Base):
    __tablename__ = "salidas_produccion"

    id = Column(Integer, primary_key=True, index=True)
    codigo_qr = Column(String, nullable=False)
    codigo_articulo = Column(String, nullable=True)
    descripcion = Column(String, nullable=False)
    lote = Column(String, nullable=True)
    fecha_vencimiento = Column(String, nullable=True)
    cantidad = Column(Integer, default=1)
    num_recibo = Column(String, nullable=True, index=True)
    turno = Column(String, nullable=True)
    grupo = Column(String, nullable=True)
    fecha_recibo = Column(String, nullable=True)
    fecha_contabilizacion = Column(String, nullable=True)
    num_op = Column(String, nullable=True)
    
    fecha_hora = Column(DateTime, default=datetime.now)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    usuario = relationship("Usuario", back_populates="salidas")