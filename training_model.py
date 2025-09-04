# -*- coding: utf-8 -*-
"""
Orman Yangını Tahmin Modeli
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from imblearn.under_sampling import RandomUnderSampler
import pickle

# 1. Veri Setini Yükle
data = pd.read_csv("tum_veriler_2020_2024_yangin_var.csv")


ozellikler = ["temp_max", "temp_min", "precipitation", "rh_max", "rh_min", "wind_max"]
X = data[ozellikler].fillna(data[ozellikler].mean())
y = data["yangin_var"]


rus = RandomUnderSampler(random_state=42)
X_res, y_res = rus.fit_resample(X, y)

print("Orijinal dağılım:", y.value_counts().to_dict())
print("Dengelenmiş dağılım:", y_res.value_counts().to_dict())

# 2. Eğitim/Test Bölünmesi
X_train, X_test, y_train, y_test = train_test_split(
    X_res, y_res, test_size=0.2, random_state=42, stratify=y_res
)

# 3. Model
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    class_weight="balanced"
)

model.fit(X_train, y_train)

# 4. Tahmin ve Performans
y_pred = model.predict(X_test)
print("\nAccuracy:", accuracy_score(y_test, y_pred))
print("\nDetaylı Rapor:")
print(classification_report(y_test, y_pred))

# 5. Modeli Kaydet
with open("orman_yangini_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("\n✅ Model başarıyla 'orman_yangini_model.pkl' olarak kaydedildi.")
