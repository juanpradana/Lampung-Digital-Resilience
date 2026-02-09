# 📡 Lampung Digital Resilience Monitor

Sistem monitoring gangguan internet dan infrastruktur digital di wilayah Provinsi Lampung secara **real-time** menggunakan pendekatan **OSINT** (Open Source Intelligence).

> Semua data yang ditampilkan adalah **data asli** — bukan dummy atau simulasi.

## 🏗️ Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────┐
│                   STREAMLIT DASHBOARD                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Peta     │  │ Ticker       │  │ Tabel Status       │  │
│  │ Folium   │  │ Real-time    │  │ Kecamatan          │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬───────────┘  │
│       │               │                   │              │
│  ┌────┴───────────────┴───────────────────┴───────────┐  │
│  │            STATUS AGGREGATION ENGINE                │  │
│  │   Combined = Social(40%) + Infra(40%) +            │  │
│  │              Disaster(20%)                          │  │
│  └──┬──────────────────┬──────────────────┬───────────┘  │
└─────┼──────────────────┼──────────────────┼──────────────┘
      │                  │                  │
┌─────┴──────┐  ┌───────┴────────┐  ┌──────┴─────────┐
│ Module A   │  │ Module B       │  │ Module C       │
│ Social     │  │ Disaster       │  │ Infrastructure │
│ Signal     │  │ Correlation    │  │ Probing        │
│            │  │                │  │                │
│ Google     │  │ BMKG API       │  │ ICMP Ping      │
│ News RSS   │  │ (autogempa,    │  │ ke 20 domain   │
│ + Search   │  │  gempaterkini, │  │ institusi      │
│ NLP/NER    │  │  gempadirasakan│  │ Lampung        │
│ Sentiment  │  │  + cuaca)      │  │ (paralel)      │
└────────────┘  └────────────────┘  └────────────────┘
```

## 📂 Struktur Folder

```
Lampung-Digital-Resilience/
├── app.py                          # Main Streamlit dashboard
├── requirements.txt                # Dependencies
├── README.md
├── .gitignore
│
├── data/
│   ├── anchors.csv                 # 20 domain institusi Lampung (real)
│   └── keywords.json               # Konfigurasi keywords NLP
│
├── modules/
│   ├── __init__.py
│   ├── bmkg_client.py              # Client API BMKG (gempa + cuaca)
│   ├── scraper.py                  # Google News RSS + Google Search
│   ├── nlp_processor.py            # NLP/NER + sentiment analysis
│   ├── social_signal.py            # Agregasi sinyal sosial
│   ├── disaster_correlation.py     # Korelasi bencana -> risiko
│   └── infra_probing.py            # Real ICMP ping via subprocess
│
├── utils/
│   ├── __init__.py
│   └── mock_data.py                # Kecamatan DB + GeoJSON generator
│
├── test_modules.py                 # Unit test NLP
└── test_real_backend.py            # Integration test semua modul
```

## 🚀 Cara Menjalankan

```bash
# 1. Clone repository
git clone https://github.com/juanpradana/Lampung-Digital-Resilience.git
cd Lampung-Digital-Resilience

# 2. Buat virtual environment
python -m venv venv

# 3. Aktifkan venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Jalankan dashboard
streamlit run app.py
```

Dashboard akan terbuka di `http://localhost:8501`.

## 🔌 Sumber Data (Semua Real)

| Module | Sumber | Endpoint / Metode |
|--------|--------|-------------------|
| **Social Signal** | Google News RSS | `news.google.com/rss/search?q=...&hl=id&gl=ID` |
| **Social Signal** | Google Search | Scraping HTML dengan `requests` + `BeautifulSoup` |
| **Disaster** | BMKG Auto Gempa | `data.bmkg.go.id/DataMKG/TEWS/autogempa.json` |
| **Disaster** | BMKG Gempa Terkini | `data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json` |
| **Disaster** | BMKG Gempa Dirasakan | `data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json` |
| **Infra Probe** | ICMP Ping | `subprocess` ping ke 20 domain `.ac.id` / `.go.id` |

Tidak memerlukan API key. Semua endpoint bersifat publik dan gratis.

## 🧠 Logika NLP: Membedakan "Jalan Rusak" vs "Jaringan Rusak"

### Masalah
Teks keluhan berbahasa Indonesia informal sering mirip secara struktur tapi berbeda domain:
- **"Jalan rusak di Kedaton"** → Infrastruktur fisik (bukan gangguan digital)
- **"Jaringan rusak di Kedaton"** → Infrastruktur digital (gangguan internet)

### Pendekatan: Keyword-Based NER + Domain Classification

Sistem menggunakan **3 lapisan analisis**:

#### Lapisan 1: Domain Keyword Matching

| Kamus | Contoh Keyword | Skor |
|-------|---------------|------|
| `digital_issue_keywords` | internet, wifi, sinyal, jaringan, indihome, modem, RTO | +1 per match |
| `non_digital_keywords` | jalan rusak, banjir jalan, air mati, sampah | +2 per match |
| `power_outage_keywords` | mati lampu, listrik padam, PLN | +1 per match |

`non_digital` diberi bobot 2x karena keyword-nya lebih spesifik (multi-word phrases).

#### Lapisan 2: Klasifikasi

```python
if non_digital_score > digital_score and power_score == 0:
    return "non_digital"
elif power_score > 0 and digital_score == 0:
    return "power_outage"
elif digital_score > 0 or power_score > 0:
    return "digital"
else:
    return "unknown"
```

#### Lapisan 3: Location Extraction (Gazetteer-Based NER)
- Daftar 50+ nama Kecamatan/Kabupaten di Lampung beserta alias (Lamsel, Lamteng, dll.)
- Case-insensitive matching, prioritas nama terpanjang
- Nama generik "Lampung" **tidak** dimasukkan karena terlalu luas

### Contoh Analisis

| Teks Input | Digital | Non-Digital | Hasil |
|-----------|---------|-------------|-------|
| "Indihome gangguan di Way Halim" | 2 | 0 | `digital` |
| "Jalan rusak parah di Kedaton" | 0 | 2 | `non_digital` |
| "Mati lampu di Rajabasa, internet ikut mati" | 1 | 0 | `digital` |
| "Sinyal Telkomsel hilang di Natar" | 2 | 0 | `digital` |

## 📊 Status Kecamatan

Status setiap kecamatan ditentukan oleh **Combined Score**:

```
Combined Score = (Social Score x 0.4) + (Infra Score x 0.4) + (Disaster Score x 0.2)
```

| Status | Warna | Kondisi |
|--------|-------|---------|
| **CRITICAL** | 🔴 Merah | Score < 30, atau Social < 40 + (Bencana / Infra Down) |
| **WARNING** | 🟡 Kuning | Score < 60, atau Social < 60, atau Infra < 60 |
| **NORMAL** | 🟢 Hijau | Score >= 60, semua indikator baik |

## 📦 Tech Stack

- **Python 3.10+**
- **Streamlit** — Dashboard framework
- **Folium** — Peta interaktif choropleth
- **Pandas** — Data processing
- **Requests** — HTTP client untuk BMKG API
- **BeautifulSoup4** — HTML parsing Google Search
- **Feedparser** — Google News RSS parsing
- **streamlit-folium** — Integrasi Folium di Streamlit

## 🧪 Testing

```bash
# Aktifkan venv terlebih dahulu, lalu:

# Unit test NLP
python test_modules.py

# Integration test semua modul (real data)
python test_real_backend.py
```

## 📝 License

MIT
