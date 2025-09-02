
"""
Orman Yangını Risk Tahmin Uygulaması - Streamlit
Gelişmiş Versiyon: Grafik + 5 Günlük Risk Tahmini
"""

import streamlit as st
import pandas as pd
import pickle
import requests
from unidecode import unidecode
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# ------------------------------
# 1️⃣ Modeli Yükle
# ------------------------------
@st.cache_resource
def load_model():
    try:
        with open("orman_yangini_model.pkl", "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        st.error("Model dosyası 'orman_yangini_model.pkl' bulunamadı.")
        st.stop()
        
@st.cache_data
def load_fire_data():
    try:
        data = pd.read_csv("tüm_veriler_birlesik_2020-2024.csv")
        data = data.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        return data
    except FileNotFoundError:
        st.error("Veri dosyası 'tüm_veriler_birlesik_2020-2024.csv' bulunamadı.")
        st.stop()

model = load_model()
fire_data_df = load_fire_data()

# ------------------------------
# 2️⃣ Hava Durumu Fonksiyonları
# ------------------------------
API_KEY = "e2cc91b090f4fdecb8b0aea827458fc6"

@st.cache_data(ttl=3600)
def get_current_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if str(data.get("cod")) == "200":
            main = data["main"]
            wind = data["wind"]
            return {
                "sıcaklık": main["temp"],
                "nem": main["humidity"],
                "rüzgar_hızı": wind["speed"]
            }
        elif str(data.get("cod")) == "401":
            st.error("❌ API key geçersiz. Lütfen API anahtarınızı kontrol edin.")
            st.stop()
        else:
            return None
    except requests.exceptions.ConnectionError:
        return "ConnectionError"


@st.cache_data(ttl=3600)
def get_5day_forecast(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if str(data.get("cod")) == "200":
            forecasts = []
            for item in data["list"]:
                dt = item["dt_txt"]
                temp = item["main"]["temp"]
                humidity = item["main"]["humidity"]
                wind = item["wind"]["speed"]
                rain = item.get("rain", {}).get("3h", 0)
                forecasts.append([dt, temp, humidity, wind, rain])
            df = pd.DataFrame(forecasts, columns=["Tarih", "Sıcaklık", "Nem", "Rüzgar", "Yağış"])
            df["Tarih"] = pd.to_datetime(df["Tarih"])
            daily_df = df[df["Tarih"].dt.hour == 12].head(5)
            return daily_df
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None

# ------------------------------
# 3️⃣ Risk Hesaplama Fonksiyonu
# ------------------------------
def calculate_risk(temp, humidity, wind, rain):
    risk = 0
    if temp > 30: risk += 2
    elif temp > 20: risk += 1
    if humidity < 30: risk += 2
    elif humidity < 50: risk += 1
    if wind > 20: risk += 2
    elif wind > 10: risk += 1
    if rain > 5: risk -= 2
    elif rain > 0: risk -= 1
    if risk <= 1: return "Düşük", "🟢"
    elif risk <= 3: return "Orta", "🟡"
    elif risk <= 5: return "Yüksek", "🟠"
    else: return "Çok Yüksek", "🔴"
# ------------------------------

city_coords = {
    "İstanbul": [41.0082, 28.9784],
    "Ankara": [39.9334, 32.8597],
    "İzmir": [38.4192, 27.1287],
    "Antalya": [36.8969, 30.7133],
    "Muğla": [37.2155, 28.3635],
    "Adana": [37.0000, 35.3213],
    "Mersin": [36.8123, 34.6415],
    "Çanakkale": [40.1462, 26.4086]
}
# ------------------------------
# 4️⃣ Streamlit Arayüzü
# ------------------------------
st.set_page_config(page_title="🔥 Orman Yangını Risk Tahmini", page_icon="🌲", layout="wide")
st.title("🔥 Orman Yangını Risk Tahmin Uygulaması")
st.markdown("Seçtiğiniz şehir için **anlık ve önümüzdeki 5 günün risk tahminini** görebilirsiniz.")


sehirler = ["İstanbul", "Ankara", "İzmir", "Antalya", "Muğla", "Adana", "Mersin", "Çanakkale"]
secilen_sehir = st.selectbox("Şehir seçin:", sehirler)
api_sehir = unidecode(secilen_sehir)

# ------------------------------
# 5️⃣ Anlık Tahmin
# ------------------------------

st.subheader(f"📌 {secilen_sehir} - Anlık Hava Durumu ve Risk Tahmini")

current_weather = get_current_weather(api_sehir)

if current_weather and current_weather != "ConnectionError":
    st.write(f"🌡️ Sıcaklık: {current_weather['sıcaklık']} °C")
    st.write(f"💧 Nem: %{current_weather['nem']}")
    st.write(f"💨 Rüzgar Hızı: {current_weather['rüzgar_hızı']} m/s")

    tahmin_veri = pd.DataFrame([{
        "temp_max": current_weather["sıcaklık"], "temp_min": current_weather["sıcaklık"],
        "precipitation": 0, "rh_max": current_weather["nem"],
        "rh_min": current_weather["nem"], "wind_max": current_weather["rüzgar_hızı"]
    }])[["temp_max", "temp_min", "precipitation", "rh_max", "rh_min", "wind_max"]]
    prob = model.predict_proba(tahmin_veri)[0][1]

    st.markdown("---")
    st.subheader("🔎 Anlık Tahmin Sonucu")
    if prob < 0.3:
        st.success(f"Düşük Risk (%{prob*100:.2f}) 🟢")
    elif prob < 0.7:
        st.warning(f"Orta Risk (%{prob*100:.2f}) 🟡")
    else:
        st.error(f"Yüksek Risk (%{prob*100:.2f}) 🔴")
else:
    st.error("Hava durumu verisi alınamadı.")

# ------------------------------
# 6️⃣ 5 Günlük Tahmin ve Grafik
# ------------------------------

st.markdown("---")
forecast_df = get_5day_forecast(api_sehir)
if forecast_df is not None:
    st.subheader(f"📅 {secilen_sehir} - 5 Günlük Risk Tahmini")
    forecast_df["Risk"] = forecast_df.apply(
        lambda x: calculate_risk(x["Sıcaklık"], x["Nem"], x["Rüzgar"], x["Yağış"]), axis=1)
    st.dataframe(forecast_df[["Tarih", "Sıcaklık", "Nem", "Rüzgar", "Yağış", "Risk"]].set_index("Tarih"))

    st.subheader("📊 Hava Faktörleri Grafiği")
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(forecast_df["Tarih"], forecast_df["Sıcaklık"], marker="o", label="Sıcaklık (°C)")
    ax.plot(forecast_df["Tarih"], forecast_df["Nem"], marker="s", label="Nem (%)")
    ax.plot(forecast_df["Tarih"], forecast_df["Rüzgar"], marker="^", label="Rüzgar (m/s)")
    ax.set_title(f"{secilen_sehir} - 5 Günlük Hava Trendleri")
    ax.legend()
    st.pyplot(fig)
else:
    st.warning("5 günlük tahmin verisi alınamadı.")

# ------------------------------
# 7️⃣ Harita
# ------------------------------

st.markdown("---")
st.header(f"{secilen_sehir} ve Çevresinde Yangın Olayları")

sehir_lat, sehir_lon = city_coords[secilen_sehir]
m = folium.Map(location=[sehir_lat, sehir_lon], zoom_start=9)

if current_weather and current_weather != "ConnectionError":
    if prob < 0.3:
        risk_color = "green"
    elif prob < 0.7:
        risk_color = "yellow"
    else:
        risk_color = "red"

    folium.Circle(
        location=[sehir_lat, sehir_lon], radius=10000, color=risk_color, fill=True,
        fill_color=risk_color, fill_opacity=0.4, tooltip=f"Tahmini Risk: %{prob * 100:.2f}"
    ).add_to(m)

filtered_df = fire_data_df[
    (fire_data_df['lat'] > sehir_lat - 1) & (fire_data_df['lat'] < sehir_lat + 1) &
    (fire_data_df['lon'] > sehir_lon - 1) & (fire_data_df['lon'] < sehir_lon + 1)
    ]

if not filtered_df.empty:
    st.subheader(f"Harita üzerinde {len(filtered_df)} yakın yangın olayı gösteriliyor.")
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in filtered_df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            icon=folium.Icon(color='red', icon='fire'),
            tooltip=f"Tarih: {row['acq_date']}<br>Sıcaklık: {row['bright_ti4']} K"
        ).add_to(marker_cluster)
else:
    st.warning(f"{secilen_sehir} ve çevresinde yangın olayı bulunamadı.")

st_folium(m, width=900, height=500)
