# models.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class Municipality(Base):
    __tablename__ = "municipalities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    geojson = Column(Text, nullable=False)  # GeoJSON'ı ham text olarak saklıyoruz
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("CriticalAsset", back_populates="municipality")

class CriticalAsset(Base):
    __tablename__ = "critical_assets"
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'Hastane', 'Okul', vb.
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    municipality = relationship("Municipality", back_populates="assets")

class NDVIRecord(Base):
    __tablename__ = "ndvi_records"
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=True)
    date = Column(DateTime, nullable=False)
    ndvi_value = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(Integer, primary_key=True, index=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=True)
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    steps = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    report_path = Column(String, nullable=True)



