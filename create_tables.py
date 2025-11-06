# create_tables.py
from db import engine, Base
import models  # modelleri import ederek Base.metadata'yi doldururuz

if __name__ == "__main__":
    print("Tablolar oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("Tamam. Veritabanı dosyası oluşturuldu (alev_kalkan.db).")
