# app.py
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import TimestampedGeoJson
from streamlit_folium import st_folium
import json
from shapely.geometry import shape
from db import SessionLocal
import models
from config import BASE_DIR
import numpy as np
import pickle
from datetime import datetime
from fpdf import FPDF
import os

# ---- Yardımcı Fonksiyonlar ----
def get_db():
    """
    Veritabanı oturumu (session) sağlar.
    yield ile birlikte kullanınca, çağıran yer try/finally mantığında db.close() çağırabilir.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def center_from_geojson(geojson_obj):
    """
    GeoJSON objesinden bounding box alır ve merkez koordinatı döner.
    geojson_obj: Python dict (json yüklenmiş hali)
    """
    # Eğer feature collection ise ilk özellikten geometri al
    if "features" in geojson_obj and len(geojson_obj["features"]) > 0:
        geom = shape(geojson_obj["features"][0]["geometry"])
    else:
        geom = shape(geojson_obj)
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    return center, bounds

def load_model(path):
    """
    Pickle ile kaydedilmiş modeli yükler.
    """
    with open(path, "rb") as f:
        return pickle.load(f)

def create_pdf_report(simulation_id, summary_text, out_path):
    """
    FPDF kullanarak basit bir PDF raporu yaratır.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Simulasyon Raporu - ID: {simulation_id}", ln=True, align="L")
    pdf.multi_cell(0, 8, txt=summary_text)
    pdf.output(out_path)
    return out_path

def spread_step(grid, wind_dir, wind_speed, drought_grid):
    """
    Cellular automata bir adım: yanan hücreler çevresini tutuşturabilir.
    grid: numpy array, 0=unburned, 1=burning, 2=burned
    wind_dir: derece (0 = doğu, 90 = kuzey)
    wind_speed: m/s
    drought_grid: same shape grid with 0..1 kuraklık skorları
    """
    new_grid = grid.copy()
    rows, cols = grid.shape
    for r in range(rows):
        for c in range(cols):
            if grid[r, c] == 1:  # eğer bu hücre yanıyorsa
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr, nc] == 0:  # komşu yanmıyorsa
                                base_p = 0.1
                                wx = np.cos(np.deg2rad(wind_dir))
                                wy = np.sin(np.deg2rad(wind_dir))
                                vec = np.array([dc, -dr])
                                dot = wx * vec[0] + wy * vec[1]
                                wind_factor = max(0, dot) * (wind_speed / 10.0)
                                drought_factor = drought_grid[nr, nc]
                                p = base_p + 0.4 * drought_factor + 0.4 * wind_factor
                                if np.random.rand() < p:
                                    new_grid[nr, nc] = 1
                new_grid[r, c] = 2
    return new_grid

def grid_to_timestamped_geojson(frames, origin_lat, origin_lon, start_time=None):
    """
    CA çıktısını folium'un TimestampedGeoJson için FeatureCollection'a çevirir.
    frames: liste halinde grid numpy array'leri
    origin_lat, origin_lon: başlangıç noktasının koordinatları
    """
    features = []
    time = start_time or datetime.utcnow()
    for t_idx, grid in enumerate(frames):
        timestamp = time.isoformat()
        rows, cols = grid.shape
        for r in range(rows):
            for c in range(cols):
                val = grid[r, c]
                if val == 1 or val == 2:
                    lat = origin_lat + (r - rows//2) * 0.0015
                    lon = origin_lon + (c - cols//2) * 0.0015
                    feature = {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": {
                            "time": timestamp,
                            "style": {"color": "red" if val == 1 else "gray", "radius": 6}
                        }
                    }
                    features.append(feature)
        # (opsiyonel) time increment ekleyebilirsin
    return {"type": "FeatureCollection", "features": features}

# ---- Streamlit arayüzü ----
st.set_page_config(layout="wide", page_title="AlevKalkan - Demo", page_icon="🔥")
st.title("AlevKalkan - Belediye Özel Yangın Analiz Platformu (Demo)")

# Sidebar: sayfalar
page = st.sidebar.selectbox("Sayfa Seç", ["Ana Panel", "Belediye Veri Yükleme", "Risk Analizi", "Yayılım Simülasyonu"])

# Model yükleme (eğer varsa)
MODEL_PATH = BASE_DIR / "orman_yangini_model.pkl"
model = None
if MODEL_PATH.exists():
    try:
        model = load_model(str(MODEL_PATH))
    except Exception as e:
        st.sidebar.warning(f"Model yüklenemedi: {e}")

# Ana Panel sayfası
if page == "Ana Panel":
    st.header("Ana Panel")
    st.markdown("Bu demo AlevKalkan'ın temel fonksiyonlarını gösterir.")
    db = next(get_db())
    municipalities = db.query(models.Municipality).all()
    st.write(f"Veritabanında {len(municipalities)} belediye kaydı var.")
    for m in municipalities:
        st.write(f"- {m.name} (ID: {m.id})")

# Belediye Veri Yükleme sayfası
elif page == "Belediye Veri Yükleme":
    st.header("Belediye Veri Yükleme")
    st.markdown("Lütfen GeoJSON sınırı ve kritik varlık CSV'si yükleyin.")

    uploaded_geo = st.file_uploader("Belediye GeoJSON dosyası", type=["geojson", "json"])
    uploaded_assets = st.file_uploader("Kritik varlıklar CSV (name,type,latitude,longitude)", type=["csv"])
    name_input = st.text_input("Belediye adı (örn: X Belediyesi)")

    if st.button("Yükle ve Kaydet"):
        if not uploaded_geo or not uploaded_assets or not name_input:
            st.error("GeoJSON, CSV ve belediye adı gereklidir.")
        else:
            geojson_obj = json.load(uploaded_geo)
            assets_df = pd.read_csv(uploaded_assets)
            db = next(get_db())
            muni = models.Municipality(name=name_input, geojson=json.dumps(geojson_obj))
            db.add(muni)
            db.commit()
            db.refresh(muni)
            for _, row in assets_df.iterrows():
                asset = models.CriticalAsset(
                    municipality_id=muni.id,
                    name=row["name"],
                    type=row.get("type", "unknown"),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"])
                )
                db.add(asset)
            db.commit()
            st.success(f"{name_input} ve varlıkları veritabanına kaydedildi (ID: {muni.id}).")

    if uploaded_geo:
        try:
            uploaded_geo.seek(0)
            geojson_obj = json.load(uploaded_geo)
            center, bounds = center_from_geojson(geojson_obj)
            m = folium.Map(location=center, zoom_start=12)
            folium.GeoJson(geojson_obj).add_to(m)
            st_folium(m, width=900, height=500)
        except Exception as e:
            st.error(f"GeoJSON gösterilemedi: {e}")

# Risk Analizi sayfası
elif page == "Risk Analizi":
    st.header("Risk Analizi - Belediye Özel")
    db = next(get_db())
    munis = db.query(models.Municipality).all()
    muni_map = {m.name: m for m in munis}
    selected = st.selectbox("Belediye seç", ["-- Seçiniz --"] + list(muni_map.keys()))

    if selected != "-- Seçiniz --":
        muni = muni_map[selected]
        geojson_obj = json.loads(muni.geojson)
        center, bounds = center_from_geojson(geojson_obj)
        m = folium.Map(location=center, zoom_start=12)
        folium.GeoJson(geojson_obj).add_to(m)
        assets = db.query(models.CriticalAsset).filter_by(municipality_id=muni.id).all()
        for a in assets:
            folium.Marker([a.latitude, a.longitude], popup=f"{a.name} ({a.type})").add_to(m)
        st_folium(m, width=900, height=500)

        st.subheader("5 günlük risk tahmini (örnek)")
        if model is None:
            st.warning("Eğitilmiş model bulunamadı. training_model.py ile modeli eğitip orman_yangini_model.pkl oluşturun.")
        else:
            st.markdown("Günlük sıcaklık, nem, rüzgar ve kuraklık skorunu girin.")
            days = 5
            temps = [st.number_input(f"Gün {i+1} - Ortalama sıcaklık (°C)", value=30.0, key=f"t{i}") for i in range(days)]
            humid = [st.number_input(f"Gün {i+1} - Nem (%)", value=30.0, key=f"h{i}") for i in range(days)]
            windspd = [st.number_input(f"Gün {i+1} - Rüzgar (m/s)", value=3.0, key=f"w{i}") for i in range(days)]
            drought_score = st.number_input("Bölge kuraklık skoru (0-1)", min_value=0.0, max_value=1.0, value=0.5)

            if st.button("Tahminleri Hesapla"):
                X = []
                for i in range(days):
                    X.append([temps[i], humid[i], windspd[i], drought_score])
                X = np.array(X)
                # XGBoost ile pickle edilmiş modelin türüne göre predict/predict_proba kullanılabilir
                try:
                    preds = model.predict(xgb.DMatrix(X)) if "xgboost" in str(type(model)).lower() else model.predict(X)
                    # Eğer model XGBoost ise yukarıdaki satır çalışır; sklearn modeller için else kısmı kullanılır.
                except Exception:
                    # fallback: model pickle ile düşük seviyede olabilir
                    preds = model.predict(X) if hasattr(model, "predict") else model.predict_proba(X)[:, 1]
                df = pd.DataFrame({
                    "day": list(range(1, days+1)),
                    "temp": temps,
                    "humidity": humid,
                    "wind": windspd,
                    "drought_score": [drought_score]*days,
                    "fire_risk": preds
                })
                st.write(df)
                st.line_chart(df[["fire_risk"]])

# Yayılım Simülasyonu sayfası
elif page == "Yayılım Simülasyonu":
    st.header("Yayılım Simülasyonu (Hücresel Otomat - Demo)")
    st.markdown("Haritaya tıklayarak başlangıç noktası belirleyin veya koordinat girin.")

    db = next(get_db())
    munis = db.query(models.Municipality).all()
    muni_map = {m.name: m for m in munis}
    selected = st.selectbox("Belediye seç (opsiyonel)", ["-- Seçiniz --"] + list(muni_map.keys()))

    if selected != "-- Seçiniz --":
        muni = muni_map[selected]
        geojson_obj = json.loads(muni.geojson)
        center, bounds = center_from_geojson(geojson_obj)
    else:
        center = [39.0, 35.0]

    m = folium.Map(location=center, zoom_start=8)
    st_map = st_folium(m, width=900, height=500)
    last_click = st_map.get("last_clicked")
    if last_click:
        st.success(f"Tıklanan nokta: {last_click}")
        start_lat = last_click["lat"]
        start_lon = last_click["lng"]
    else:
        start_lat = st.number_input("Başlangıç Lat", value=center[0])
        start_lon = st.number_input("Başlangıç Lon", value=center[1])

    wind_speed = st.number_input("Rüzgar hızı (m/s)", value=3.0)
    wind_dir = st.number_input("Rüzgar yönü (deg, 0=doğu, 90=kuzey)", value=0.0)
    drought_score = st.number_input("Kuraklık skoru (0-1)", min_value=0.0, max_value=1.0, value=0.6)
    steps = st.slider("Adım sayısı (1 adım = 1 dakika)", 5, 30, 10)

    if st.button("Simülasyonu Başlat"):
        rows, cols = 31, 31
        grid = np.zeros((rows, cols), dtype=int)
        origin = (rows//2, cols//2)
        grid[origin] = 1
        drought_grid = np.ones((rows, cols)) * drought_score
        frames = [grid.copy()]
        for i in range(steps):
            grid = spread_step(grid, wind_dir, wind_speed, drought_grid)
            frames.append(grid.copy())
        ts_geojson = grid_to_timestamped_geojson(frames, start_lat, start_lon, start_time=datetime.utcnow())
        m2 = folium.Map(location=[start_lat, start_lon], zoom_start=12)
        TimestampedGeoJson(
            data=ts_geojson,
            transition_time=200,
            period="PT1M",
            add_last_point=True,
            loop=False,
            auto_play=False,
            max_speed=1
        ).add_to(m2)
        st_folium(m2, width=900, height=500)

        sim = models.Simulation(
            municipality_id=muni.id if selected != "-- Seçiniz --" else None,
            start_lat=start_lat,
            start_lon=start_lon,
            steps=steps
        )
        db.add(sim)
        db.commit()
        db.refresh(sim)
        summary = f"Simülasyon ID: {sim.id}\nBaşlangıç: {start_lat}, {start_lon}\nAdım sayısı: {steps}\nRüzgar: {wind_speed} m/s, yön: {wind_dir}°\nKuraklık skoru: {drought_score}"
        out_path = str(BASE_DIR / f"sim_report_{sim.id}.pdf")
        create_pdf_report(sim.id, summary, out_path)
        sim.report_path = out_path
        db.commit()
        st.success("Simülasyon tamamlandı. PDF rapor oluşturuldu.")
        st.download_button("Raporu İndir", data=open(out_path, "rb"), file_name=os.path.basename(out_path), mime="application/pdf")
        if st.button("Riskli mahallelere uyarı gönder (proto)"):
            st.success("Riskli mahallelere uyarı gönderildi!")
