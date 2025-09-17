"""
Orman Yangını Risk Tahmin Uygulaması - Streamlit
Gelişmiş Versiyon
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
# 1️⃣ Modeli Yükleme
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
        data = pd.read_csv("tum_veriler_2020_2024_yangin_var.csv")
        data = data.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        data['acq_date'] = pd.to_datetime(data['acq_date'])
        return data
    except FileNotFoundError:
        st.error("Veri dosyası 'tum_veriler_2020_2024_yangin_var.csv' bulunamadı.")
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
    if temp > 30:
        risk += 2
    elif temp > 20:
        risk += 1
    if humidity < 30:
        risk += 2
    elif humidity < 50:
        risk += 1
    if wind > 20:
        risk += 2
    elif wind > 10:
        risk += 1
    if rain > 5:
        risk -= 2
    elif rain > 0:
        risk -= 1
    if risk <= 1:
        return "Düşük", "🟢"
    elif risk <= 3:
        return "Orta", "🟡"
    elif risk <= 5:
        return "Yüksek", "🟠"
    else:
        return "Çok Yüksek", "🔴"

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
    }])["temp_max temp_min precipitation rh_max rh_min wind_max".split()]
    prob = model.predict_proba(tahmin_veri)[0][1]
    #Skoru normalize etmek (0.2 ile 0.9 arasına sıkıştır)
    prob = 0.2 + (prob * 0.7)

    st.markdown("---")
    st.subheader("🔎 Anlık Tahmin Sonucu")
    if prob < 0.3:
        st.success(f"Düşük Risk (%{prob * 100:.2f}) 🟢")
    elif prob < 0.7:
        st.warning(f"Orta Risk (%{prob * 100:.2f}) 🟡")
    else:
        st.error(f"Yüksek Risk (%{prob * 100:.2f}) 🔴")
else:
    st.error("Hava durumu verisi alınamadı.")

# ------------------------------
# 6️⃣ 5 Günlük Tahmin ve Grafik               
# ------------------------------
st.markdown("---")
forecast_df = get_5day_forecast(api_sehir)

if forecast_df is not None and not forecast_df.empty:
    st.subheader(f"📅 {secilen_sehir} - 5 Günlük Risk Tahmini")
    forecast_df = forecast_df.copy()
    forecast_df["Risk_seviyesi"] = forecast_df.apply(
        lambda x: calculate_risk(x["Sıcaklık"], x["Nem"], x["Rüzgar"], x["Yağış"])[0], axis=1)
    forecast_df["Risk_emoji"] = forecast_df.apply(
        lambda x: calculate_risk(x["Sıcaklık"], x["Nem"], x["Rüzgar"], x["Yağış"])[1], axis=1)

    st.dataframe(forecast_df[["Tarih", "Sıcaklık", "Nem", "Rüzgar", "Yağış", "Risk_seviyesi", "Risk_emoji"]]
                 .set_index("Tarih"))

    st.subheader("📊 Hava Faktörleri Grafiği")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(forecast_df["Tarih"], forecast_df["Sıcaklık"], marker="o", label="Sıcaklık (°C)")
    ax.plot(forecast_df["Tarih"], forecast_df["Nem"], marker="s", label="Nem (%)")
    ax.plot(forecast_df["Tarih"], forecast_df["Rüzgar"], marker="^", label="Rüzgar (m/s)")
    ax.set_title(f"{secilen_sehir} - 5 Günlük Hava Trendleri")
    ax.set_xlabel("Tarih")
    ax.set_ylabel("Değer")
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)
else:
    st.warning("5 günlük tahmin verisi alınamadı. Hava verisi yoksa API veya internet bağlantınızı kontrol edin.")
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5, "5 günlük veri alınamadı", ha='center', va='center')
    ax.axis('off')
    st.pyplot(fig)

# ------------------------------
# 7️⃣ Harita (GÜNCELLEME)
# ------------------------------
st.markdown("---")
st.header(f"{secilen_sehir} ve Çevresinde Yangın Olayları")

if not pd.api.types.is_datetime64_any_dtype(fire_data_df['acq_date']):
    fire_data_df['acq_date'] = pd.to_datetime(fire_data_df['acq_date'], errors='coerce')

all_years = sorted(fire_data_df['acq_date'].dt.year.dropna().astype(int).unique().tolist())
selected_years = st.multiselect("Görüntülenecek Yılları Seçin:", options=all_years, default=all_years)

sehir_lat, sehir_lon = city_coords[secilen_sehir]
m = folium.Map(location=[sehir_lat, sehir_lon], zoom_start=9)

try:
    if 'prob' in locals():
        if prob < 0.3:
            risk_color = "green"
        elif prob < 0.7:
            risk_color = "orange"
        else:
            risk_color = "red"

        folium.Circle(
            location=[sehir_lat, sehir_lon], radius=10000, color=risk_color, fill=True,
            fill_color=risk_color, fill_opacity=0.25,
            tooltip=f"Tahmini Risk: %{prob * 100:.2f}"
        ).add_to(m)
except Exception:
    pass

filtered_by_years_df = fire_data_df[fire_data_df['acq_date'].dt.year.isin(selected_years)].copy()
final_filtered_df = filtered_by_years_df[
    (filtered_by_years_df['lat'] > sehir_lat - 1) & (filtered_by_years_df['lat'] < sehir_lat + 1) &
    (filtered_by_years_df['lon'] > sehir_lon - 1) & (filtered_by_years_df['lon'] < sehir_lon + 1)
].copy()

MAX_MARKERS = 2000
if not final_filtered_df.empty:
    count = len(final_filtered_df)
    st.subheader(f"Harita üzerinde {count} yakın yangın olayı (gösterim sınırlı).")
    if count > MAX_MARKERS:
        st.info(f"Çok fazla nokta ({count}) bulundu — performans için son {MAX_MARKERS} kayıt gösteriliyor.")
        final_filtered_df = final_filtered_df.sort_values("acq_date", ascending=False).head(MAX_MARKERS)

    marker_cluster = MarkerCluster()
    for _, row in final_filtered_df.iterrows():
        try:
            popup_html = folium.Popup(
                f"Tarih: {row['acq_date'].strftime('%Y-%m-%d')}<br>"
                f"Sıcaklık (bright_ti4): {row.get('bright_ti4', 'NA')}", max_width=250)
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=4,
                color='red',
                fill=True,
                fill_opacity=0.7,
                popup=popup_html
            ).add_to(marker_cluster)
        except Exception:
            continue
    marker_cluster.add_to(m)
else:
    st.warning(f"{secilen_sehir} ve çevresinde seçili yıllar için yangın olayı bulunamadı.")

st_folium(m, width=900, height=500)
                     
