# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# create_engine: SQLAlchemy için veri tabanı motoru yaratır
# connect_args={"check_same_thread": False} : SQLite + çoklu thread/Streamlit uyumu için
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# sessionmaker: veritabanı işlemleri için "oturum" üretir
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: modellerimizin (tablo tanımlarımızın) kalıtım temelidir
Base = declarative_base()

