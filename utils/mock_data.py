"""
Mock Data Generator untuk Lampung Digital Resilience Monitor.
Menghasilkan data simulasi untuk semua modul karena keterbatasan akses API/scraping.
"""

import random
import json
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# Kecamatan Database Lampung
# ============================================================
KECAMATAN_DB = {
    "Tanjung Karang Pusat": {"kabupaten": "Bandar Lampung", "lat": -5.4175, "lon": 105.2621},
    "Tanjung Karang Barat": {"kabupaten": "Bandar Lampung", "lat": -5.4200, "lon": 105.2400},
    "Tanjung Karang Timur": {"kabupaten": "Bandar Lampung", "lat": -5.4150, "lon": 105.2750},
    "Teluk Betung Utara": {"kabupaten": "Bandar Lampung", "lat": -5.4294, "lon": 105.2618},
    "Teluk Betung Barat": {"kabupaten": "Bandar Lampung", "lat": -5.4500, "lon": 105.2400},
    "Teluk Betung Selatan": {"kabupaten": "Bandar Lampung", "lat": -5.4600, "lon": 105.2550},
    "Kedaton": {"kabupaten": "Bandar Lampung", "lat": -5.3950, "lon": 105.2500},
    "Sukarame": {"kabupaten": "Bandar Lampung", "lat": -5.3836, "lon": 105.2717},
    "Way Halim": {"kabupaten": "Bandar Lampung", "lat": -5.3900, "lon": 105.2850},
    "Rajabasa": {"kabupaten": "Bandar Lampung", "lat": -5.3648, "lon": 105.2436},
    "Kemiling": {"kabupaten": "Bandar Lampung", "lat": -5.3800, "lon": 105.2200},
    "Langkapura": {"kabupaten": "Bandar Lampung", "lat": -5.3700, "lon": 105.2350},
    "Enggal": {"kabupaten": "Bandar Lampung", "lat": -5.4260, "lon": 105.2580},
    "Kedamaian": {"kabupaten": "Bandar Lampung", "lat": -5.4100, "lon": 105.2700},
    "Labuhan Ratu": {"kabupaten": "Bandar Lampung", "lat": -5.3750, "lon": 105.2650},
    "Sukabumi": {"kabupaten": "Bandar Lampung", "lat": -5.4050, "lon": 105.2900},
    "Tanjung Senang": {"kabupaten": "Bandar Lampung", "lat": -5.3700, "lon": 105.2950},
    "Way Kandis": {"kabupaten": "Bandar Lampung", "lat": -5.3600, "lon": 105.2550},
    "Metro Pusat": {"kabupaten": "Metro", "lat": -5.1140, "lon": 105.3060},
    "Metro Timur": {"kabupaten": "Metro", "lat": -5.1100, "lon": 105.3200},
    "Metro Barat": {"kabupaten": "Metro", "lat": -5.1180, "lon": 105.2900},
    "Kalianda": {"kabupaten": "Lampung Selatan", "lat": -5.7230, "lon": 105.6170},
    "Natar": {"kabupaten": "Lampung Selatan", "lat": -5.3100, "lon": 105.2800},
    "Jati Agung": {"kabupaten": "Lampung Selatan", "lat": -5.3300, "lon": 105.3000},
    "Tanjung Bintang": {"kabupaten": "Lampung Selatan", "lat": -5.3500, "lon": 105.3600},
    "Sidomulyo": {"kabupaten": "Lampung Selatan", "lat": -5.5500, "lon": 105.5500},
    "Bakauheni": {"kabupaten": "Lampung Selatan", "lat": -5.8700, "lon": 105.7500},
    "Pringsewu": {"kabupaten": "Pringsewu", "lat": -5.3580, "lon": 104.9830},
    "Gunung Sugih": {"kabupaten": "Lampung Tengah", "lat": -4.8800, "lon": 105.2700},
    "Terbanggi Besar": {"kabupaten": "Lampung Tengah", "lat": -4.8400, "lon": 105.2900},
    "Kotabumi": {"kabupaten": "Lampung Utara", "lat": -4.8300, "lon": 104.8900},
    "Sukadana": {"kabupaten": "Lampung Timur", "lat": -5.3900, "lon": 105.5100},
    "Gedong Tataan": {"kabupaten": "Pesawaran", "lat": -5.3900, "lon": 105.0800},
    "Kota Agung": {"kabupaten": "Tanggamus", "lat": -5.4900, "lon": 104.6300},
    "Liwa": {"kabupaten": "Lampung Barat", "lat": -5.0500, "lon": 104.0700},
    "Blambangan Umpu": {"kabupaten": "Way Kanan", "lat": -4.6500, "lon": 104.5500},
    "Menggala": {"kabupaten": "Tulang Bawang", "lat": -4.5400, "lon": 105.2400},
    "Tulang Bawang Tengah": {"kabupaten": "Tulang Bawang Barat", "lat": -4.4500, "lon": 105.0500},
}

PROVIDERS = ["Indihome", "Biznet", "Telkomsel", "XL", "Smartfren", "Tri", "PLN", "MyRepublic", "FirstMedia"]

COMPLAINT_TEMPLATES = [
    "Udah {durasi} {provider} {masalah} di daerah {lokasi}. Kapan benernya?",
    "{provider} {masalah} lagi di {lokasi}. Tiap hari gini terus!",
    "Ada yang ngalamin {provider} {masalah} di {lokasi}? Dari tadi pagi nih.",
    "Tolong dong @{provider_handle} sinyal di {lokasi} {masalah}. Mau kerja susah.",
    "Mati lampu di {lokasi} udah {durasi}. Internet juga ikut mati.",
    "Hujan deras di {lokasi}, {provider} langsung {masalah}. Payah!",
    "Baru pasang {provider} di {lokasi} udah {masalah} aja. Nyesel.",
    "Internet {provider} di {lokasi} {masalah}. WFH jadi WFNgapain.",
    "Sinyal {provider} hilang total di {lokasi}. Ada gangguan kah?",
    "Sejak tadi malam {provider} di {lokasi} {masalah}. Mohon perbaikan segera.",
    "Jaringan {provider} di {lokasi} {masalah}, mau meeting online gabisa.",
    "Listrik mati di {lokasi}, otomatis internet juga down semua.",
    "Wifi {provider} di {lokasi} RTO terus. Ada yang sama?",
    "Gangguan {provider} area {lokasi}? Ping tinggi banget {masalah}.",
    "Di {lokasi} {provider} lemot parah, buffering mulu nonton drakor.",
]

MASALAH_LIST = [
    "mati total", "gangguan", "down", "lemot banget", "putus nyambung",
    "RTO terus", "sinyal hilang", "tidak bisa konek", "error terus",
    "lambat parah", "buffering mulu", "disconnect terus", "timeout",
]

DURASI_LIST = ["2 jam", "3 jam", "sejak pagi", "sejak semalam", "seharian", "dari kemarin"]

PROVIDER_HANDLES = {
    "Indihome": "IndiHomeCare", "Biznet": "BiznetHome", "Telkomsel": "Telkomsel",
    "XL": "XaborXL", "Smartfren": "smartfikiranmu", "Tri": "3aborCare",
    "PLN": "paborln_123", "MyRepublic": "MyRepublic", "FirstMedia": "FirstMediaCares",
}

# Non-digital complaints (noise) for NLP testing
NOISE_TEMPLATES = [
    "Jalan rusak parah di {lokasi}, kapan diperbaiki?",
    "Banjir di {lokasi} bikin macet total.",
    "Pohon tumbang di {lokasi} halangi jalan.",
    "Air PDAM mati di {lokasi} udah 2 hari.",
    "Sampah menumpuk di {lokasi}, bau banget.",
]


def get_kecamatan_list():
    """Mengembalikan daftar semua kecamatan."""
    return list(KECAMATAN_DB.keys())


def get_kecamatan_info(kecamatan_name):
    """Mengembalikan info kecamatan (kabupaten, lat, lon)."""
    return KECAMATAN_DB.get(kecamatan_name)


def generate_social_complaints(count=20, noise_ratio=0.15):
    """
    Menghasilkan data simulasi keluhan sosial media.
    noise_ratio: proporsi keluhan non-digital (untuk menguji NLP filter).
    """
    complaints = []
    now = datetime.now()
    noise_count = int(count * noise_ratio)
    digital_count = count - noise_count

    for i in range(digital_count):
        kecamatan = random.choice(list(KECAMATAN_DB.keys()))
        provider = random.choice(PROVIDERS)
        masalah = random.choice(MASALAH_LIST)
        durasi = random.choice(DURASI_LIST)
        template = random.choice(COMPLAINT_TEMPLATES)

        text = template.format(
            provider=provider,
            masalah=masalah,
            lokasi=kecamatan,
            durasi=durasi,
            provider_handle=PROVIDER_HANDLES.get(provider, provider),
        )

        timestamp = now - timedelta(minutes=random.randint(1, 180))

        complaints.append({
            "id": f"tweet_{i:04d}",
            "timestamp": timestamp.isoformat(),
            "text": text,
            "source": random.choice(["twitter", "google_search"]),
            "username": f"user_{random.randint(1000, 9999)}",
        })

    for i in range(noise_count):
        kecamatan = random.choice(list(KECAMATAN_DB.keys()))
        template = random.choice(NOISE_TEMPLATES)
        text = template.format(lokasi=kecamatan)
        timestamp = now - timedelta(minutes=random.randint(1, 180))

        complaints.append({
            "id": f"tweet_{digital_count + i:04d}",
            "timestamp": timestamp.isoformat(),
            "text": text,
            "source": random.choice(["twitter", "google_search"]),
            "username": f"user_{random.randint(1000, 9999)}",
        })

    random.shuffle(complaints)
    return complaints


def generate_earthquake_data():
    """Menghasilkan data simulasi gempa BMKG."""
    now = datetime.now()
    earthquakes = []

    if random.random() < 0.4:
        mag = round(random.uniform(3.0, 6.5), 1)
        lat = round(random.uniform(-6.0, -4.5), 4)
        lon = round(random.uniform(104.0, 106.0), 4)
        depth = random.randint(5, 100)

        earthquakes.append({
            "timestamp": (now - timedelta(minutes=random.randint(10, 120))).isoformat(),
            "magnitude": mag,
            "depth_km": depth,
            "latitude": lat,
            "longitude": lon,
            "location": f"{depth} km {'Barat Daya' if random.random() > 0.5 else 'Tenggara'} Lampung",
            "source": "BMKG",
        })

    return earthquakes


def generate_weather_warnings():
    """Menghasilkan data simulasi peringatan cuaca BMKG."""
    warnings = []
    now = datetime.now()

    warning_types = [
        {"type": "Hujan Lebat", "level": "WARNING", "impact": "Potensi banjir dan longsor"},
        {"type": "Angin Kencang", "level": "WARNING", "impact": "Potensi pohon tumbang dan kerusakan infrastruktur"},
        {"type": "Gelombang Tinggi", "level": "ADVISORY", "impact": "Potensi gangguan pelayaran"},
        {"type": "Cuaca Ekstrem", "level": "ALERT", "impact": "Potensi gangguan infrastruktur luas"},
    ]

    affected_areas = random.sample(list(KECAMATAN_DB.keys()), k=random.randint(0, 8))

    if affected_areas and random.random() < 0.5:
        warning = random.choice(warning_types)
        warnings.append({
            "timestamp": (now - timedelta(minutes=random.randint(5, 60))).isoformat(),
            "type": warning["type"],
            "level": warning["level"],
            "impact": warning["impact"],
            "affected_kecamatan": affected_areas,
            "source": "BMKG Lampung",
        })

    return warnings


def generate_ping_results(anchors_df):
    """
    Menghasilkan data simulasi ping ke anchor points.
    Beberapa kecamatan akan disimulasikan mengalami gangguan (RTO).
    """
    results = []
    troubled_kecamatan = random.sample(
        list(KECAMATAN_DB.keys()),
        k=random.randint(1, 5)
    )

    for _, row in anchors_df.iterrows():
        kecamatan = row["Kecamatan"]
        is_troubled = kecamatan in troubled_kecamatan

        if is_troubled:
            if random.random() < 0.6:
                latency = -1  # RTO
                packet_loss = 100.0
                status = "RTO"
            else:
                latency = round(random.uniform(200, 2000), 1)
                packet_loss = round(random.uniform(30, 80), 1)
                status = "HIGH_LATENCY"
        else:
            latency = round(random.uniform(5, 80), 1)
            packet_loss = round(random.uniform(0, 5), 1)
            status = "OK"

        results.append({
            "ip": row["IP_Address"],
            "nama_lokasi": row["Nama_Lokasi"],
            "kecamatan": kecamatan,
            "kabupaten": row.get("Kabupaten", ""),
            "latency_ms": latency,
            "packet_loss_pct": packet_loss,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })

    return results


def generate_geojson_lampung():
    """
    Menghasilkan GeoJSON sederhana untuk kecamatan di Lampung.
    Menggunakan polygon persegi kecil di sekitar titik pusat setiap kecamatan.
    """
    features = []
    size = 0.04  # ukuran polygon (derajat)

    for kecamatan, info in KECAMATAN_DB.items():
        lat = info["lat"]
        lon = info["lon"]

        jitter = random.uniform(-0.005, 0.005)
        coords = [[
            [lon - size + jitter, lat - size],
            [lon + size + jitter, lat - size],
            [lon + size - jitter, lat + size],
            [lon - size - jitter, lat + size],
            [lon - size + jitter, lat - size],
        ]]

        feature = {
            "type": "Feature",
            "properties": {
                "kecamatan": kecamatan,
                "kabupaten": info["kabupaten"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": coords,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }
