# -*- coding: utf-8 -*-
"""
Orman Yangını Tahmin Modeli
"""

# 1. Gerekli Kütüphaneleri İçeri Aktarma
# ------------------------------------------
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

# 2. Veri Setini Yükleme
# ------------------------------------------
try:
    data = pd.read_csv("tüm_veriler_birlesik_2020-2024.csv")
except FileNotFoundError:
    print("HATA: 'tüm_veriler_birlesik_2020-2024.csv' dosyası bulunamadı.")
    print("Lütfen dosya yolunu kontrol edin.")
    exit()

# 3. Veriyi Anlama ve Hazırlama
# ------------------------------------------

data['yangin_var'] = 1


data_no_fire = data.copy()
data_no_fire['yangin_var'] = 0

data = pd.concat([data, data_no_fire], ignore_index=True)

ozellikler = ['temp_max', 'temp_min', 'precipitation', 'rh_max', 'rh_min', 'wind_max']
X = data[ozellikler]
y = data['yangin_var']

# 4. Veri Setini Eğitim ve Test Olarak Ayırma
# ------------------------------------------
X_egitim, X_test, y_egitim, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Eğitim veri sayısı: {X_egitim.shape[0]}")
print(f"Test veri sayısı: {X_test.shape[0]}")

# 5. Modeli Oluşturma ve Eğitme
# ------------------------------------------
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)

model.fit(X_egitim, y_egitim)

# 6. Modelin Başarısını Değerlendirme
# ------------------------------------------
y_tahmin = model.predict(X_test)

print("\nModelin Test Başarısı:")
print(f"Doğruluk Skoru: {accuracy_score(y_test, y_tahmin):.2f}")
print("\nDetaylı Rapor:")
print(classification_report(y_test, y_tahmin))

# 7. Modeli Kaydetme
# ------------------------------------------
with open("orman_yangini_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("\n✅ Model başarıyla 'orman_yangini_model.pkl' olarak kaydedildi.")

