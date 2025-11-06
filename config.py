# config.py
from pathlib import Path
import os

# BASE_DIR: bu dosyanın olduğu klasör (proje kökü)
BASE_DIR = Path(__file__).resolve().parent

# DB_PATH: veritabanı (SQLite) dosyasının yolu
DB_PATH = BASE_DIR / "alev_kalkan.db"

# DATABASE_URL: SQLAlchemy'nin kullanacağı bağlantı stringi
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Sentinel Hub veya diğer API anahtarlarını .env'den çekmek için
SENTINELHUB_INSTANCE_ID = os.getenv("cfd02faa-d170-4665-8939-1ecaeac10c5f", "")
SENTINELHUB_CLIENT_ID = os.getenv("32832155-bd6f-4b02-bbf3-8e71329e60d6", "")
SENTINELHUB_CLIENT_SECRET = os.getenv("B4uNvvEF6tOF04tqIo9wcpMIHPOHcz39", "")
