"""
Disaster Correlation Module - The "Physical Cause" Module.

Modul ini bertanggung jawab untuk:
1. Mengambil data gempa REAL dari API publik BMKG
2. Mengambil peringatan cuaca REAL dari BMKG
3. Menentukan wilayah berisiko tinggi berdasarkan korelasi bencana
"""

import logging
import math
from datetime import datetime

from modules.bmkg_client import fetch_all_earthquakes, fetch_weather_warnings_lampung
from utils.mock_data import KECAMATAN_DB

logger = logging.getLogger(__name__)


def fetch_disaster_data():
    """
    Mengambil data bencana terkini REAL dari API BMKG.

    Returns:
        dict: {earthquakes: list, weather_warnings: list}
    """
    earthquakes = fetch_all_earthquakes()
    weather_warnings = fetch_weather_warnings_lampung()

    logger.info(
        "Disaster data: %d gempa, %d peringatan cuaca",
        len(earthquakes), len(weather_warnings),
    )

    return {
        "earthquakes": earthquakes,
        "weather_warnings": weather_warnings,
    }


def haversine_distance(lat1, lon1, lat2, lon2):
    """Hitung jarak antara dua titik koordinat dalam km."""
    R = 6371  # radius bumi dalam km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def assess_earthquake_risk(earthquakes):
    """
    Tentukan kecamatan yang terdampak gempa.

    Logic:
    - Gempa >= 5.0 SR: radius dampak 100 km -> HIGH RISK
    - Gempa 4.0-4.9 SR: radius dampak 50 km -> MEDIUM RISK
    - Gempa < 4.0 SR: radius dampak 25 km -> LOW RISK
    """
    affected = {}

    for eq in earthquakes:
        mag = eq["magnitude"]
        eq_lat = eq["latitude"]
        eq_lon = eq["longitude"]

        if mag >= 5.0:
            radius = 100
            risk = "HIGH"
        elif mag >= 4.0:
            radius = 50
            risk = "MEDIUM"
        else:
            radius = 25
            risk = "LOW"

        for kec, info in KECAMATAN_DB.items():
            dist = haversine_distance(eq_lat, eq_lon, info["lat"], info["lon"])
            if dist <= radius:
                if kec not in affected or _risk_level(risk) > _risk_level(affected[kec]["risk"]):
                    affected[kec] = {
                        "risk": risk,
                        "cause": f"Gempa {mag} SR",
                        "distance_km": round(dist, 1),
                        "earthquake_detail": eq,
                    }

    return affected


def assess_weather_risk(weather_warnings):
    """
    Tentukan kecamatan yang terdampak peringatan cuaca.

    Logic:
    - ALERT level: HIGH RISK
    - WARNING level: MEDIUM RISK
    - ADVISORY level: LOW RISK
    """
    affected = {}

    for warning in weather_warnings:
        level = warning["level"]
        risk_map = {"ALERT": "HIGH", "WARNING": "MEDIUM", "ADVISORY": "LOW"}
        risk = risk_map.get(level, "LOW")

        for kec in warning.get("affected_kecamatan", []):
            if kec not in affected or _risk_level(risk) > _risk_level(affected[kec]["risk"]):
                affected[kec] = {
                    "risk": risk,
                    "cause": warning["type"],
                    "warning_detail": warning,
                }

    return affected


def _risk_level(risk_str):
    """Konversi risk string ke numerik untuk perbandingan."""
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(risk_str, 0)


def get_combined_disaster_risk():
    """
    Gabungkan semua data bencana dan hasilkan peta risiko per kecamatan.

    Returns:
        dict: {
            kecamatan: {risk, causes: list, details: dict},
            _metadata: {earthquakes, weather_warnings}
        }
    """
    data = fetch_disaster_data()
    eq_risk = assess_earthquake_risk(data["earthquakes"])
    weather_risk = assess_weather_risk(data["weather_warnings"])

    combined = {}

    all_kecamatan = set(list(eq_risk.keys()) + list(weather_risk.keys()))

    for kec in all_kecamatan:
        causes = []
        max_risk = "LOW"

        if kec in eq_risk:
            causes.append(eq_risk[kec]["cause"])
            if _risk_level(eq_risk[kec]["risk"]) > _risk_level(max_risk):
                max_risk = eq_risk[kec]["risk"]

        if kec in weather_risk:
            causes.append(weather_risk[kec]["cause"])
            if _risk_level(weather_risk[kec]["risk"]) > _risk_level(max_risk):
                max_risk = weather_risk[kec]["risk"]

        combined[kec] = {
            "risk": max_risk,
            "causes": causes,
            "eq_detail": eq_risk.get(kec),
            "weather_detail": weather_risk.get(kec),
        }

    return {
        "risk_map": combined,
        "metadata": {
            "earthquakes": data["earthquakes"],
            "weather_warnings": data["weather_warnings"],
        },
    }
