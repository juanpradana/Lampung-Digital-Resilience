"""
BMKG Client - Mengambil data gempa bumi dan cuaca REAL dari API publik BMKG.

Endpoints:
- Auto Gempa (terbaru): https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json
- Gempa Terkini (15 terbaru M>=5): https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json
- Gempa Dirasakan (15 terbaru): https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json

Semua endpoint gratis, tanpa API key.
"""

import logging
import re
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

BMKG_AUTO_GEMPA = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
BMKG_GEMPA_TERKINI = "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json"
BMKG_GEMPA_DIRASAKAN = "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json"

REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": "LampungDigitalResilience/1.0",
    "Accept": "application/json",
}


def _parse_coordinates(coord_str):
    """Parse string koordinat BMKG, e.g. '-7.82,130.25' -> (lat, lon)."""
    try:
        parts = coord_str.split(",")
        return float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return None, None


def _parse_magnitude(mag_str):
    """Parse magnitude string, e.g. '5.9' -> 5.9."""
    try:
        return float(mag_str)
    except (ValueError, TypeError):
        return 0.0


def _parse_depth(depth_str):
    """Parse kedalaman, e.g. '100 km' -> 100."""
    try:
        return int(re.search(r"\d+", str(depth_str)).group())
    except (AttributeError, ValueError):
        return 0


def _normalize_gempa(raw, source_label=""):
    """Normalisasi satu record gempa BMKG ke format internal."""
    coords = raw.get("Coordinates", "")
    lat, lon = _parse_coordinates(coords)

    dt_str = raw.get("DateTime", "")
    try:
        timestamp = datetime.fromisoformat(dt_str).isoformat()
    except (ValueError, TypeError):
        tanggal = raw.get("Tanggal", "")
        jam = raw.get("Jam", "")
        timestamp = f"{tanggal} {jam}"

    return {
        "timestamp": timestamp,
        "magnitude": _parse_magnitude(raw.get("Magnitude", "0")),
        "depth_km": _parse_depth(raw.get("Kedalaman", "0")),
        "latitude": lat,
        "longitude": lon,
        "location": raw.get("Wilayah", "Tidak diketahui"),
        "dirasakan": raw.get("Dirasakan", ""),
        "potensi": raw.get("Potensi", ""),
        "source": f"BMKG {source_label}".strip(),
    }


def fetch_auto_gempa():
    """
    Ambil data gempa terbaru (auto) dari BMKG.
    Returns: list berisi 1 dict gempa, atau list kosong jika gagal.
    """
    try:
        resp = requests.get(BMKG_AUTO_GEMPA, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("Infogempa", {}).get("gempa", {})
        if raw:
            return [_normalize_gempa(raw, "AutoGempa")]
        return []
    except Exception as e:
        logger.error("Gagal fetch auto gempa BMKG: %s", e)
        return []


def fetch_gempa_terkini():
    """
    Ambil 15 gempa terkini (M>=5) dari BMKG.
    Returns: list of dict gempa.
    """
    try:
        resp = requests.get(BMKG_GEMPA_TERKINI, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("Infogempa", {}).get("gempa", [])
        return [_normalize_gempa(g, "GempaTerkini") for g in raw_list]
    except Exception as e:
        logger.error("Gagal fetch gempa terkini BMKG: %s", e)
        return []


def fetch_gempa_dirasakan():
    """
    Ambil 15 gempa dirasakan terbaru dari BMKG.
    Returns: list of dict gempa.
    """
    try:
        resp = requests.get(BMKG_GEMPA_DIRASAKAN, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("Infogempa", {}).get("gempa", [])
        return [_normalize_gempa(g, "GempaDirasakan") for g in raw_list]
    except Exception as e:
        logger.error("Gagal fetch gempa dirasakan BMKG: %s", e)
        return []


def fetch_all_earthquakes():
    """
    Gabungkan semua sumber data gempa BMKG, deduplikasi berdasarkan timestamp+magnitude.
    Returns: list of dict gempa, sorted by timestamp desc.
    """
    all_quakes = []
    all_quakes.extend(fetch_auto_gempa())
    all_quakes.extend(fetch_gempa_terkini())
    all_quakes.extend(fetch_gempa_dirasakan())

    # Deduplikasi
    seen = set()
    unique = []
    for q in all_quakes:
        key = (q["timestamp"], q["magnitude"])
        if key not in seen:
            seen.add(key)
            unique.append(q)

    # Filter hanya yang punya koordinat valid
    valid = [q for q in unique if q["latitude"] is not None and q["longitude"] is not None]

    # Sort by timestamp desc
    valid.sort(key=lambda x: x["timestamp"], reverse=True)
    return valid


def fetch_weather_warnings_lampung():
    """
    Ambil peringatan cuaca untuk wilayah Lampung.

    BMKG tidak menyediakan API JSON khusus peringatan cuaca per provinsi
    yang mudah diakses. Sebagai gantinya, kita cek data gempa yang
    menyebutkan wilayah Lampung dan gunakan cuaca dari feed berita.

    Untuk cuaca, kita akan menggunakan pendekatan scraping dari
    halaman peringatan dini BMKG jika tersedia.

    Returns: list of dict peringatan cuaca.
    """
    warnings = []
    try:
        url = "https://data.bmkg.go.id/DataMKG/TEWS/cuaca_lampung.json"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Parse cuaca data jika tersedia
            _parse_bmkg_weather(data, warnings)
    except Exception as e:
        logger.warning("Cuaca Lampung endpoint tidak tersedia: %s", e)

    # Fallback: cek peringatan dini dari halaman BMKG
    try:
        url_warn = "https://data.bmkg.go.id/DataMKG/TEWS/warning.json"
        resp = requests.get(url_warn, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            _parse_bmkg_warning(data, warnings)
    except Exception as e:
        logger.warning("Warning endpoint tidak tersedia: %s", e)

    return warnings


def _parse_bmkg_weather(data, warnings):
    """Parse data cuaca BMKG dan ekstrak peringatan untuk Lampung."""
    try:
        # Struktur data cuaca BMKG bervariasi, coba parse yang umum
        if isinstance(data, dict):
            for area_key, area_data in data.items():
                if isinstance(area_data, list):
                    for item in area_data:
                        if isinstance(item, dict):
                            desc = str(item.get("cuaca", "")).lower()
                            if any(w in desc for w in ["hujan lebat", "petir", "angin kencang"]):
                                warnings.append({
                                    "timestamp": datetime.now().isoformat(),
                                    "type": item.get("cuaca", "Peringatan Cuaca"),
                                    "level": "WARNING",
                                    "impact": "Potensi gangguan infrastruktur",
                                    "affected_kecamatan": [],
                                    "source": "BMKG Cuaca",
                                    "raw": item,
                                })
    except Exception as e:
        logger.warning("Gagal parse cuaca BMKG: %s", e)


def _parse_bmkg_warning(data, warnings):
    """Parse data peringatan dini BMKG."""
    try:
        if isinstance(data, dict):
            issues = data.get("issues", data.get("warning", []))
            if isinstance(issues, list):
                for item in issues:
                    desc = str(item).lower()
                    if "lampung" in desc:
                        warnings.append({
                            "timestamp": datetime.now().isoformat(),
                            "type": "Peringatan Dini BMKG",
                            "level": "WARNING",
                            "impact": str(item),
                            "affected_kecamatan": [],
                            "source": "BMKG Warning",
                        })
    except Exception as e:
        logger.warning("Gagal parse warning BMKG: %s", e)
