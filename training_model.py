# =============================================================
# training_model.py
# Türkiye'deki orman yangınlarını tahmin eden XGBoost modeli
# =============================================================

# Gerekli kütüphaneleri yüklüyoruz.
# Bunlar: veri işlemede pandas, modellemede xgboost, kaydetmede pickle.
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
import xgboost as xgb
import pickle
from pathlib import Path

# -------------------------------------------------------------
# 1️⃣ Dosya yollarını tanımla
# -------------------------------------------------------------
# Path, dosya konumlarını işletim sisteminden bağımsız tanımlamamızı sağlar.
BASE = Path(__file__).resolve().parent  # Bu dosyanın bulunduğu klasör
DATA_PATH = BASE / "tum_veriler_2020_2024_yangin_var.csv"  # Veri dosyasının konumu
MODEL_OUT = BASE / "orman_yangini_model.pkl"                # Eğitilen modelin kaydedileceği dosya

# -------------------------------------------------------------
# 2️⃣ Veriyi oku
# -------------------------------------------------------------
# CSV dosyasını pandas ile okuyoruz.
df = pd.read_csv(DATA_PATH)

# Sütun isimlerini görmek için terminale yazdırıyoruz.
print("Veri sütunları:", df.columns.tolist())

# -------------------------------------------------------------
# 3️⃣ Ortalama sıcaklık sütununu oluştur
# -------------------------------------------------------------
# Bazı verilerde "temperature" yok ama "temp_max" ve "temp_min" var.
# Bu iki değerin ortalamasını alarak yeni bir "temperature" sütunu oluşturuyoruz.
if "temperature" not in df.columns:
    if "temp_max" in df.columns and "temp_min" in df.columns:
        df["temperature"] = (df["temp_max"] + df["temp_min"]) / 2
        print("Yeni 'temperature' sütunu oluşturuldu (temp_max ve temp_min ortalaması).")
    else:
        raise KeyError("❌ temperature, temp_max veya temp_min sütunu bulunamadı. Lütfen CSV dosyasını kontrol edin.")
    

if "humidity" not in df.columns:
    if "rh_max" in df.columns and "rh_min" in df.columns:
        df["humidity"] = (df["rh_max"] + df["rh_min"]) / 2
        print("Yeni 'humidity' sütunu oluşturuldu (rh_max ve rh_min ortalaması).")
    else:
        raise KeyError("❌ humidity, rh_max veya rh_min sütunu bulunamadı. Lütfen CSV dosyasını kontrol edin.")
    


if "wind_speed" not in df.columns:
    if "wind_max" in df.columns :
        df["wind_speed"] = df["wind_max"]
        print("Yeni 'wind_speed' sütunu oluşturuldu (wind_max kopyalandı).")
    else:
        raise KeyError("❌ wind_speed veya wind_max sütunu bulunamadı. Lütfen CSV dosyasını kontrol edin.")

if "fire_occurred" not in df.columns:
    if "yangin_var" in df.columns :
        df["fire_occurred"] = df["yangin_var"]
        print("Yeni 'fire_occurred' sütunu oluşturuldu (yangin_var kopyalandı).")
    else:
        raise KeyError("❌ fire_occurred veya yangin_var sütunu bulunamadı. Lütfen CSV dosyasını kontrol edin.")


# -------------------------------------------------------------
# 4️⃣ Kuraklık skoru ekle
# -------------------------------------------------------------
# Kuraklık skoru yoksa, sıcaklık ve nem verilerini kullanarak basit bir tahmini skor üretiriz.
if "kuraklik_skoru" not in df.columns:
    # Sıcaklık ve nemi 0-1 aralığında normalize ederiz.
    t_norm = (df["temperature"] - df["temperature"].min()) / (df["temperature"].max() - df["temperature"].min())
    h_norm = 1 - (df["humidity"] - df["humidity"].min()) / (df["humidity"].max() - df["humidity"].min())

    # Kuraklık skorunu ağırlıklı ortalama olarak hesaplıyoruz.
    df["kuraklik_skoru"] = (t_norm * 0.6 + h_norm * 0.4)
    print("Yeni 'kuraklik_skoru' sütunu eklendi.")

# -------------------------------------------------------------
# 5️⃣ Özellikleri (features) ve hedef değişkeni (label) belirle
# -------------------------------------------------------------
features = ["temperature", "humidity", "wind_speed", "kuraklik_skoru"]

# Eksik değer içeren satırları atıyoruz (model hata vermesin diye)
df = df.dropna(subset=features + ["fire_occurred"])

# Giriş verileri (X) ve hedef değişken (y)
X = df[features].values
y = df["fire_occurred"].astype(int).values

# -------------------------------------------------------------
# 6️⃣ Veriyi eğitim ve test olarak ayır
# -------------------------------------------------------------
# Verinin %80'i eğitim, %20'si test için kullanılacak.
# stratify=y → her iki kümede de yangın/yangın-yok oranı aynı kalır.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -------------------------------------------------------------
# 7️⃣ XGBoost veri formatına dönüştür (DMatrix)
# -------------------------------------------------------------
# XGBoost, kendi özel veri yapısını (DMatrix) kullanır. Bu hız kazandırır.
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# -------------------------------------------------------------
# 8️⃣ Model parametreleri
# -------------------------------------------------------------
# Bu ayarlar modelin öğrenme şeklini belirler.
params = {
    "objective": "binary:logistic",   # İkili sınıflandırma (yangın var/yok)
    "eval_metric": "auc",             # Modelin başarısını AUC metriğiyle ölç
    "max_depth": 6,                   # Karar ağacı derinliği
    "eta": 0.1,                       # Öğrenme hızı (düşükse daha yavaş ama güvenli öğrenir)
    "subsample": 0.8,                 # Her iterasyonda veri alt örnekleme oranı
    "colsample_bytree": 0.8,          # Her ağaç için sütun alt örnekleme oranı
    "seed": 42                        # Rastgelelik için sabit tohum
}

# -------------------------------------------------------------
# 9️⃣ Modeli eğit
# -------------------------------------------------------------
# early_stopping_rounds → 20 tur boyunca gelişme yoksa erken durdurur.
bst = xgb.train(
    params,
    dtrain,
    num_boost_round=200,                # Maksimum 200 ağaç (tur)
    evals=[(dtest, "test")],
    early_stopping_rounds=20,
    verbose_eval=10                    # Her 10 turda bir ilerlemeyi yazdırır
)

# -------------------------------------------------------------
# 🔟 Modeli test et
# -------------------------------------------------------------
preds = bst.predict(dtest)

# Tahminler 0-1 arasında olasılıklar → 0.5 üzerindekileri 1 (yangın var) kabul ediyoruz.
auc = roc_auc_score(y_test, preds)
acc = accuracy_score(y_test, (preds > 0.5).astype(int))

print(f"\n🎯 Model Performansı:")
print(f" - AUC: {auc:.4f}")
print(f" - Doğruluk (ACC): {acc:.4f}")

# -------------------------------------------------------------
# 1️⃣1️⃣ Modeli kaydet
# -------------------------------------------------------------
with open(MODEL_OUT, "wb") as f:
    pickle.dump(bst, f)

print(f"\n✅ Model başarıyla kaydedildi: {MODEL_OUT}")

# -------------------------------------------------------------
# 1️⃣2️⃣ (Opsiyonel) İlk 5 satırı yazdır
# -------------------------------------------------------------
print("\nVeri örneği (ilk 5 satır):")
print(df[features + ['fire_occurred']].head())
