from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
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
    rol = Column(String, default="analista")  # analista, almacenista, coordinador, webmaster
    
    # Recuperación de clave
    pregunta_secreta = Column(String, nullable=True)
    respuesta_secreta_hash = Column(String, nullable=True)

    # Relaciones
    salidas = relationship("SalidaProduccion", foreign_keys="[SalidaProduccion.usuario_id]", back_populates="usuario", cascade="all, delete-orphan")
    recepciones = relationship("SalidaProduccion", foreign_keys="[SalidaProduccion.usuario_recepcion_id]", back_populates="usuario_recepcion")


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

    # --- CAMPOS DE CONCILIACIÓN DE ALMACÉN ---
    recibido_almacen = Column(Boolean, default=False, nullable=False)
    fecha_hora_recepcion = Column(DateTime, nullable=True)
    usuario_recepcion_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Relaciones
    usuario = relationship("Usuario", foreign_keys=[usuario_id], back_populates="salidas")
    usuario_recepcion = relationship("Usuario", foreign_keys=[usuario_recepcion_id], back_populates="recepciones")