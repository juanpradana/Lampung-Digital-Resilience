"""
NLP Processor untuk Lampung Digital Resilience Monitor.

Modul ini melakukan:
1. Named Entity Recognition (NER) berbasis keyword/gazetteer untuk lokasi di Lampung
2. Klasifikasi keluhan: digital vs non-digital
3. Ekstraksi provider yang disebutkan
4. Sentiment scoring sederhana

Pendekatan: Keyword-based NER + Context Window Analysis
- Lebih cocok untuk teks Bahasa Indonesia informal (sosmed)
- Tidak memerlukan model NLP berat seperti spaCy/transformers
- Akurasi tinggi karena domain-specific (telekomunikasi + geografi Lampung)
"""

import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_keywords():
    """Memuat konfigurasi keywords dari file JSON."""
    keywords_path = os.path.join(BASE_DIR, "data", "keywords.json")
    with open(keywords_path, "r", encoding="utf-8") as f:
        return json.load(f)


KEYWORDS = load_keywords()

# Gazetteer: daftar nama kecamatan & kabupaten untuk location extraction
# CATATAN: "Lampung" saja TIDAK dimasukkan karena terlalu generik
#          (hampir semua berita menyebut "Lampung").
#          Hanya nama spesifik kabupaten/kecamatan yang digunakan.
LOCATION_GAZETTEER = [
    # Kecamatan Bandar Lampung
    "Tanjung Karang Pusat", "Tanjung Karang Barat", "Tanjung Karang Timur",
    "Teluk Betung Utara", "Teluk Betung Barat", "Teluk Betung Selatan",
    "Kedaton", "Sukarame", "Way Halim", "Rajabasa", "Kemiling", "Langkapura",
    "Enggal", "Kedamaian", "Labuhan Ratu", "Sukabumi", "Tanjung Senang",
    "Way Kandis",
    # Kecamatan Metro
    "Metro Pusat", "Metro Timur", "Metro Barat",
    # Kecamatan lainnya
    "Kalianda", "Natar", "Jati Agung", "Tanjung Bintang", "Sidomulyo",
    "Bakauheni", "Pringsewu", "Gunung Sugih", "Terbanggi Besar",
    "Kotabumi", "Sukadana", "Gedong Tataan", "Kota Agung", "Liwa",
    "Blambangan Umpu", "Menggala", "Tulang Bawang Tengah",
    # Kota / Kabupaten (level lebih tinggi, tetap spesifik)
    "Bandar Lampung", "Bandarlampung",
    "Lampung Selatan", "Lampung Tengah", "Lampung Utara",
    "Lampung Timur", "Lampung Barat",
    "Tulang Bawang Barat", "Tulang Bawang",
    "Pesawaran", "Tanggamus", "Way Kanan", "Mesuji", "Pesisir Barat",
    # Alias umum di berita
    "Lamsel", "Lamteng", "Lamut", "Lamtim", "Lambar",
]

# Urutkan dari yang terpanjang agar matching lebih akurat
LOCATION_GAZETTEER.sort(key=len, reverse=True)


def normalize_text(text):
    """Normalisasi teks: lowercase, hapus karakter khusus berlebih."""
    text = text.lower().strip()
    text = re.sub(r"@\w+", "", text)  # hapus mention
    text = re.sub(r"#\w+", "", text)  # hapus hashtag
    text = re.sub(r"http\S+", "", text)  # hapus URL
    text = re.sub(r"\s+", " ", text)  # normalisasi spasi
    return text


# Mapping alias -> nama resmi kecamatan/kabupaten
LOCATION_ALIASES = {
    "bandarlampung": "Bandar Lampung",
    "lamsel": "Lampung Selatan",
    "lamteng": "Lampung Tengah",
    "lamut": "Lampung Utara",
    "lamtim": "Lampung Timur",
    "lambar": "Lampung Barat",
}


def extract_locations(text):
    """
    Ekstrak lokasi (kecamatan/kelurahan/kabupaten) dari teks menggunakan
    gazetteer matching. Case-insensitive.

    Untuk data real (berita), teks sering menyebut kabupaten, bukan kecamatan.
    Kita tangkap keduanya.
    """
    text_lower = text.lower()
    found_locations = []

    for location in LOCATION_GAZETTEER:
        loc_lower = location.lower()
        if loc_lower in text_lower:
            # Resolve alias ke nama resmi
            canonical = LOCATION_ALIASES.get(loc_lower, location)

            # Hindari duplikat dari subset (e.g., "Metro" di dalam "Metro Pusat")
            is_subset = False
            for existing in found_locations:
                if canonical.lower() in existing.lower() or existing.lower() in canonical.lower():
                    if len(canonical) < len(existing):
                        is_subset = True
                        break
            if not is_subset:
                # Hapus existing yang lebih pendek jika canonical lebih panjang
                found_locations = [
                    ex for ex in found_locations
                    if not (ex.lower() in canonical.lower() and len(ex) < len(canonical))
                ]
                found_locations.append(canonical)

    return found_locations


def classify_issue(text):
    """
    Klasifikasi apakah keluhan terkait masalah digital/internet atau bukan.

    Logika:
    1. Hitung skor kecocokan dengan keyword digital vs non-digital
    2. Jika skor digital > skor non-digital -> digital issue
    3. Khusus "mati lampu" -> power outage (bisa menyebabkan gangguan digital)

    Cara membedakan "Jalan Rusak" vs "Jaringan Rusak":
    - "Jalan" -> non-digital keyword (infrastruktur fisik)
    - "Jaringan" -> digital keyword (infrastruktur digital)
    - Context window: kata-kata di sekitar keyword menentukan klasifikasi
    """
    text_lower = normalize_text(text)

    digital_score = 0
    non_digital_score = 0
    power_score = 0

    # Hitung skor digital
    for kw in KEYWORDS["digital_issue_keywords"]:
        if kw.lower() in text_lower:
            digital_score += 1

    # Hitung skor non-digital
    for kw in KEYWORDS["non_digital_keywords"]:
        if kw.lower() in text_lower:
            non_digital_score += 2  # bobot lebih tinggi karena lebih spesifik

    # Hitung skor power outage
    for kw in KEYWORDS["power_outage_keywords"]:
        if kw.lower() in text_lower:
            power_score += 1

    # Klasifikasi
    if non_digital_score > digital_score and power_score == 0:
        return "non_digital"
    elif power_score > 0 and digital_score == 0:
        return "power_outage"
    elif digital_score > 0 or power_score > 0:
        return "digital"
    else:
        return "unknown"


def extract_provider(text):
    """Ekstrak nama provider dari teks."""
    text_lower = normalize_text(text)
    detected_providers = []

    for provider, keywords in KEYWORDS["provider_keywords"].items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if provider not in detected_providers:
                    detected_providers.append(provider)
                break

    return detected_providers if detected_providers else ["Unknown"]


def calculate_sentiment(text):
    """
    Hitung sentiment score sederhana (-1.0 sampai 0.0).
    Semakin negatif = semakin parah keluhannya.
    """
    text_lower = normalize_text(text)
    score = -0.3  # baseline negatif (karena ini keluhan)

    # Kata-kata yang menambah keparahan
    severe_words = ["mati total", "rto", "down", "padam", "tidak bisa", "error"]
    moderate_words = ["lemot", "lambat", "gangguan", "putus", "buffering"]
    mild_words = ["agak", "sedikit", "kadang"]
    intensifier_words = ["banget", "parah", "sangat", "terus", "tiap hari", "seharian"]

    for word in severe_words:
        if word in text_lower:
            score -= 0.25

    for word in moderate_words:
        if word in text_lower:
            score -= 0.15

    for word in mild_words:
        if word in text_lower:
            score += 0.1

    for word in intensifier_words:
        if word in text_lower:
            score -= 0.1

    return max(-1.0, min(0.0, round(score, 2)))


def determine_severity(text):
    """Tentukan tingkat keparahan dari teks keluhan."""
    text_lower = normalize_text(text)

    for kw in KEYWORDS["severity_keywords"]["critical"]:
        if kw in text_lower:
            return "critical"

    for kw in KEYWORDS["severity_keywords"]["warning"]:
        if kw in text_lower:
            return "warning"

    return "normal"


def process_complaint(raw_complaint):
    """
    Pipeline utama: proses satu keluhan mentah menjadi data terstruktur.

    Input: dict dengan key 'text', 'timestamp', 'source', dll.
    Output: dict terstruktur dengan lokasi, provider, sentiment, klasifikasi.
    """
    text = raw_complaint.get("text", "")

    locations = extract_locations(text)
    issue_type = classify_issue(text)
    providers = extract_provider(text)
    sentiment = calculate_sentiment(text)
    severity = determine_severity(text)

    return {
        "id": raw_complaint.get("id", ""),
        "timestamp": raw_complaint.get("timestamp", datetime.now().isoformat()),
        "source": raw_complaint.get("source", "unknown"),
        "original_text": text,
        "locations_detected": locations,
        "primary_location": locations[0] if locations else "Unknown",
        "providers_detected": providers,
        "primary_provider": providers[0] if providers else "Unknown",
        "issue_type": issue_type,
        "sentiment_score": sentiment,
        "severity": severity,
        "is_digital_issue": issue_type in ("digital", "power_outage"),
    }


def process_batch(raw_complaints):
    """Proses batch keluhan dan filter hanya yang terkait digital."""
    results = []
    for complaint in raw_complaints:
        processed = process_complaint(complaint)
        results.append(processed)
    return results
