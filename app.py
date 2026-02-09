"""
Lampung Digital Resilience Monitor
===================================
Dashboard Streamlit untuk monitoring gangguan internet dan infrastruktur digital
di wilayah Provinsi Lampung secara real-time menggunakan OSINT.

Jalankan: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import folium
import json
from datetime import datetime
from streamlit_folium import st_folium

from modules.social_signal import fetch_social_signals, aggregate_by_kecamatan, get_social_score
from modules.disaster_correlation import get_combined_disaster_risk
from modules.infra_probing import probe_anchors, aggregate_probe_by_kecamatan, get_infra_score
from utils.mock_data import KECAMATAN_DB, generate_geojson_lampung

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="Lampung Digital Resilience Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Custom CSS — universal (works on both light & dark themes)
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: inherit;
        text-align: center;
        padding: 0.5rem 0;
    }
    .sub-header {
        font-size: 1rem;
        opacity: 0.7;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    .metric-card h3 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: white !important;
    }
    .metric-card p {
        margin: 0.3rem 0 0 0;
        font-size: 0.85rem;
        opacity: 0.9;
        color: white !important;
    }
    .status-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .status-yellow {
        background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
    }
    .status-red {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    }
    .ticker-item {
        padding: 0.6rem 0.8rem;
        margin: 0.3rem 0;
        border-left: 4px solid #667eea;
        background: rgba(128, 128, 128, 0.1);
        color: inherit;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
    }
    .ticker-item b, .ticker-item small {
        color: inherit;
    }
    .ticker-critical {
        border-left-color: #eb3349;
        background: rgba(235, 51, 73, 0.12);
    }
    .ticker-warning {
        border-left-color: #F2994A;
        background: rgba(242, 153, 74, 0.12);
    }
    .disaster-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.1rem;
    }
    .badge-high { background: #dc2626; color: #ffffff; }
    .badge-medium { background: #d97706; color: #ffffff; }
    .badge-low { background: #2563eb; color: #ffffff; }
    .app-footer {
        text-align: center;
        opacity: 0.5;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Data Loading (cached)
# ============================================================
@st.cache_data(ttl=60)
def load_all_data():
    """Muat semua data dari ketiga modul."""
    # Module A: Social Signals (REAL - Google News RSS + Google Search)
    social_signals = fetch_social_signals()
    social_agg = aggregate_by_kecamatan(social_signals)
    social_scores = get_social_score(social_agg)

    # Module B: Disaster Correlation (REAL - BMKG API)
    disaster_data = get_combined_disaster_risk()

    # Module C: Infrastructure Probing (REAL - ICMP Ping)
    probe_results = probe_anchors()
    probe_agg = aggregate_probe_by_kecamatan(probe_results)
    infra_scores = get_infra_score(probe_agg)

    return {
        "social_signals": social_signals,
        "social_agg": social_agg,
        "social_scores": social_scores,
        "disaster_data": disaster_data,
        "probe_results": probe_results,
        "probe_agg": probe_agg,
        "infra_scores": infra_scores,
    }


def compute_kecamatan_status(data):
    """
    Hitung status akhir setiap kecamatan berdasarkan 3 sumber data.

    Status Logic:
    - CRITICAL (Merah): Laporan sosmed tinggi + bencana alam / IP RTO
    - WARNING (Kuning): Laporan sosmed meningkat
    - NORMAL (Hijau): Tidak ada indikasi gangguan
    """
    statuses = {}
    disaster_risk_map = data["disaster_data"]["risk_map"]

    for kec in KECAMATAN_DB:
        social_score = data["social_scores"].get(kec, 100)
        infra_score = data["infra_scores"].get(kec, 100)
        has_disaster = kec in disaster_risk_map
        disaster_risk = disaster_risk_map.get(kec, {}).get("risk", "NONE")

        # Combined score (weighted)
        combined = (social_score * 0.4) + (infra_score * 0.4) + (
            0 if disaster_risk == "HIGH" else 50 if disaster_risk == "MEDIUM" else 100
        ) * 0.2

        if combined < 30 or (social_score < 40 and (has_disaster or infra_score < 50)):
            status = "CRITICAL"
            color = "#eb3349"
        elif combined < 60 or social_score < 60 or infra_score < 60:
            status = "WARNING"
            color = "#F2994A"
        else:
            status = "NORMAL"
            color = "#38ef7d"

        statuses[kec] = {
            "status": status,
            "color": color,
            "combined_score": round(combined, 1),
            "social_score": social_score,
            "infra_score": infra_score,
            "disaster_risk": disaster_risk,
            "disaster_causes": disaster_risk_map.get(kec, {}).get("causes", []),
        }

    return statuses


def build_map(statuses, data):
    """Bangun peta Folium choropleth Lampung."""
    # Pusat Lampung
    m = folium.Map(
        location=[-5.25, 105.1],
        zoom_start=8,
        tiles="CartoDB positron",
    )

    geojson = generate_geojson_lampung()

    # Tambahkan status ke properties GeoJSON
    for feature in geojson["features"]:
        kec = feature["properties"]["kecamatan"]
        status_info = statuses.get(kec, {})
        feature["properties"]["status"] = status_info.get("status", "NORMAL")
        feature["properties"]["combined_score"] = status_info.get("combined_score", 100)
        feature["properties"]["social_score"] = status_info.get("social_score", 100)
        feature["properties"]["infra_score"] = status_info.get("infra_score", 100)
        feature["properties"]["disaster_risk"] = status_info.get("disaster_risk", "NONE")

    def style_function(feature):
        status = feature["properties"].get("status", "NORMAL")
        color_map = {
            "CRITICAL": "#eb3349",
            "WARNING": "#F2994A",
            "NORMAL": "#38ef7d",
        }
        return {
            "fillColor": color_map.get(status, "#38ef7d"),
            "color": "#333333",
            "weight": 1,
            "fillOpacity": 0.65,
        }

    folium.GeoJson(
        geojson,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["kecamatan", "kabupaten", "status", "combined_score"],
            aliases=["Kecamatan:", "Kabupaten:", "Status:", "Skor:"],
            style="font-size: 12px;",
        ),
        popup=folium.GeoJsonPopup(
            fields=["kecamatan", "status", "social_score", "infra_score", "disaster_risk"],
            aliases=["Kecamatan", "Status", "Skor Sosmed", "Skor Infra", "Risiko Bencana"],
        ),
    ).add_to(m)

    # Tambahkan marker untuk anchor points
    probe_agg = data["probe_agg"]
    for result in data["probe_results"]:
        kec = result["kecamatan"]
        info = KECAMATAN_DB.get(kec)
        if not info:
            continue

        icon_color = "green" if result["status"] == "OK" else "orange" if result["status"] == "HIGH_LATENCY" else "red"
        lat_text = f"{result['latency_ms']}ms" if result["latency_ms"] >= 0 else "RTO"
        host_label = result.get("host", result.get("ip", ""))

        folium.CircleMarker(
            location=[info["lat"], info["lon"]],
            radius=6,
            color=icon_color,
            fill=True,
            fill_color=icon_color,
            fill_opacity=0.8,
            tooltip=f"{result['nama_lokasi']} ({host_label}): {lat_text} | Loss: {result['packet_loss_pct']}%",
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: rgba(30,30,30,0.9); padding: 12px 16px; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.4); font-size: 13px; color: #e2e8f0;">
        <b>Status Konektivitas</b><br>
        <span style="color: #38ef7d;">&#9632;</span> Normal<br>
        <span style="color: #F2994A;">&#9632;</span> Warning<br>
        <span style="color: #eb3349;">&#9632;</span> Critical<br>
        <br><b>Anchor Points</b><br>
        <span style="color: #38ef7d;">&#9679;</span> OK &nbsp;
        <span style="color: #F2994A;">&#9679;</span> High Latency &nbsp;
        <span style="color: #eb3349;">&#9679;</span> RTO
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# ============================================================
# Main App
# ============================================================
def main():
    # Header
    st.markdown('<div class="main-header">📡 Lampung Digital Resilience Monitor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Monitoring Gangguan Internet & Infrastruktur Digital Provinsi Lampung | OSINT-Based</div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown("## 🏛️ Prov. Lampung")
        st.markdown("### ⚙️ Pengaturan")

        if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
            st.cache_data.clear()

        st.markdown("---")
        st.markdown("### 📊 Filter")
        show_social = st.checkbox("Social Signals", value=True)
        show_disaster = st.checkbox("Disaster Data", value=True)
        show_infra = st.checkbox("Infrastructure Probes", value=True)

        st.markdown("---")
        st.markdown("### ℹ️ Tentang")
        st.markdown(
            "Sistem ini menggabungkan data **laporan sosial media**, "
            "**data bencana alam BMKG**, dan **active network probing** "
            "untuk menyimpulkan status konektivitas internet di Lampung."
        )
        st.markdown(f"*Terakhir diperbarui: {datetime.now().strftime('%H:%M:%S')}*")

    # Load data
    data = load_all_data()
    statuses = compute_kecamatan_status(data)

    # ---- Metrics Row ----
    critical_count = sum(1 for s in statuses.values() if s["status"] == "CRITICAL")
    warning_count = sum(1 for s in statuses.values() if s["status"] == "WARNING")
    normal_count = sum(1 for s in statuses.values() if s["status"] == "NORMAL")
    total_complaints = sum(1 for s in data["social_signals"] if s.get("is_digital_issue", False))
    eq_count = len(data["disaster_data"]["metadata"]["earthquakes"])
    warning_weather = len(data["disaster_data"]["metadata"]["weather_warnings"])

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f'<div class="metric-card status-red"><h3>{critical_count}</h3><p>Kecamatan Critical</p></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card status-yellow"><h3>{warning_count}</h3><p>Kecamatan Warning</p></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card status-green"><h3>{normal_count}</h3><p>Kecamatan Normal</p></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="metric-card"><h3>{total_complaints}</h3><p>Laporan Digital</p></div>',
            unsafe_allow_html=True,
        )
    with col5:
        disaster_total = eq_count + warning_weather
        css_class = "status-red" if disaster_total > 0 else ""
        st.markdown(
            f'<div class="metric-card {css_class}"><h3>{disaster_total}</h3><p>Peringatan Bencana</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ---- Main Content: Map + Ticker ----
    map_col, ticker_col = st.columns([3, 1])

    with map_col:
        st.markdown("### 🗺️ Peta Status Konektivitas Lampung")
        folium_map = build_map(statuses, data)
        st_folium(folium_map, width=None, height=520, returned_objects=[])

    with ticker_col:
        st.markdown("### 📰 Ticker Laporan Terkini")

        digital_signals = [s for s in data["social_signals"] if s.get("is_digital_issue", False)]
        digital_signals.sort(key=lambda x: x["timestamp"], reverse=True)

        for signal in digital_signals[:15]:
            severity = signal.get("severity", "normal")
            css_class = (
                "ticker-critical" if severity == "critical"
                else "ticker-warning" if severity == "warning"
                else ""
            )
            time_str = signal["timestamp"][11:16] if len(signal["timestamp"]) > 16 else ""
            provider = signal.get("primary_provider", "")
            location = signal.get("primary_location", "")

            st.markdown(
                f'<div class="ticker-item {css_class}">'
                f'<b>{time_str}</b> | <b>{provider}</b> @ {location}<br>'
                f'<small>{signal["original_text"][:120]}...</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ---- Detail Sections ----
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tabel Status Kecamatan",
        "🌐 Social Signal Detail",
        "🌋 Data Bencana",
        "🔌 Infrastructure Probes",
    ])

    with tab1:
        st.markdown("### Status Seluruh Kecamatan")
        rows = []
        for kec, info in statuses.items():
            kab = KECAMATAN_DB[kec]["kabupaten"]
            rows.append({
                "Kecamatan": kec,
                "Kabupaten": kab,
                "Status": info["status"],
                "Skor Gabungan": info["combined_score"],
                "Skor Sosmed": info["social_score"],
                "Skor Infra": info["infra_score"],
                "Risiko Bencana": info["disaster_risk"],
                "Penyebab Bencana": ", ".join(info["disaster_causes"]) if info["disaster_causes"] else "-",
            })

        df_status = pd.DataFrame(rows)
        df_status = df_status.sort_values("Skor Gabungan", ascending=True)

        def color_status(val):
            if val == "CRITICAL":
                return "background-color: #dc2626; color: #ffffff; font-weight: bold"
            elif val == "WARNING":
                return "background-color: #d97706; color: #ffffff; font-weight: bold"
            return "background-color: #059669; color: #ffffff"

        styled = df_status.style.map(color_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True, height=400)

    with tab2:
        if show_social:
            st.markdown("### Analisis Social Signal")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("#### Keluhan per Kecamatan")
                social_agg = data["social_agg"]
                if social_agg:
                    agg_rows = []
                    for kec, agg in social_agg.items():
                        providers_str = ", ".join([f"{p}({c})" for p, c in agg["top_providers"]])
                        agg_rows.append({
                            "Kecamatan": kec,
                            "Jumlah Keluhan": agg["complaint_count"],
                            "Avg Sentiment": agg["avg_sentiment"],
                            "Severity Max": agg["max_severity"],
                            "Top Provider": providers_str,
                        })
                    df_agg = pd.DataFrame(agg_rows).sort_values("Jumlah Keluhan", ascending=False)
                    st.dataframe(df_agg, use_container_width=True)
                else:
                    st.info("Tidak ada keluhan digital terdeteksi.")

            with col_b:
                st.markdown("#### Semua Laporan (termasuk noise)")
                all_signals = data["social_signals"]
                signal_rows = []
                for s in all_signals:
                    signal_rows.append({
                        "Waktu": s["timestamp"][11:19] if len(s["timestamp"]) > 19 else s["timestamp"],
                        "Lokasi": s.get("primary_location", "?"),
                        "Provider": s.get("primary_provider", "?"),
                        "Tipe": s.get("issue_type", "?"),
                        "Severity": s.get("severity", "?"),
                        "Digital?": "✅" if s.get("is_digital_issue") else "❌",
                        "Teks": s["original_text"][:80],
                    })
                df_signals = pd.DataFrame(signal_rows)
                st.dataframe(df_signals, use_container_width=True, height=400)

    with tab3:
        if show_disaster:
            st.markdown("### Data Bencana Alam")

            metadata = data["disaster_data"]["metadata"]

            col_eq, col_weather = st.columns(2)

            with col_eq:
                st.markdown("#### 🌍 Data Gempa Bumi")
                earthquakes = metadata["earthquakes"]
                if earthquakes:
                    for eq in earthquakes:
                        mag = eq["magnitude"]
                        badge_class = "badge-high" if mag >= 5.0 else "badge-medium" if mag >= 4.0 else "badge-low"
                        st.markdown(
                            f'<div class="ticker-item">'
                            f'<span class="disaster-badge {badge_class}">{mag} SR</span> '
                            f'{eq["location"]}<br>'
                            f'<small>Kedalaman: {eq["depth_km"]} km | {eq["timestamp"][:16]}</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("Tidak ada gempa signifikan terdeteksi.")

            with col_weather:
                st.markdown("#### 🌧️ Peringatan Cuaca")
                warnings = metadata["weather_warnings"]
                if warnings:
                    for w in warnings:
                        badge_class = (
                            "badge-high" if w["level"] == "ALERT"
                            else "badge-medium" if w["level"] == "WARNING"
                            else "badge-low"
                        )
                        affected = ", ".join(w["affected_kecamatan"][:5])
                        more = f" +{len(w['affected_kecamatan']) - 5} lainnya" if len(w["affected_kecamatan"]) > 5 else ""
                        st.markdown(
                            f'<div class="ticker-item">'
                            f'<span class="disaster-badge {badge_class}">{w["level"]}</span> '
                            f'<b>{w["type"]}</b><br>'
                            f'<small>Dampak: {w["impact"]}</small><br>'
                            f'<small>Area: {affected}{more}</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("Tidak ada peringatan cuaca aktif.")

            st.markdown("#### Kecamatan Terdampak Bencana")
            risk_map = data["disaster_data"]["risk_map"]
            if risk_map:
                risk_rows = []
                for kec, info in risk_map.items():
                    risk_rows.append({
                        "Kecamatan": kec,
                        "Risk Level": info["risk"],
                        "Penyebab": ", ".join(info["causes"]),
                    })
                df_risk = pd.DataFrame(risk_rows).sort_values("Risk Level")
                st.dataframe(df_risk, use_container_width=True)
            else:
                st.success("Tidak ada kecamatan yang terdampak bencana saat ini.")

    with tab4:
        if show_infra:
            st.markdown("### Infrastructure Probe Results")

            probe_agg = data["probe_agg"]

            col_summary, col_detail = st.columns(2)

            with col_summary:
                st.markdown("#### Ringkasan per Kecamatan")
                if probe_agg:
                    probe_rows = []
                    for kec, info in probe_agg.items():
                        probe_rows.append({
                            "Kecamatan": kec,
                            "Status": info["overall_status"],
                            "Avg Latency (ms)": str(info["avg_latency"]) if info["avg_latency"] >= 0 else "RTO",
                            "Avg Packet Loss (%)": str(round(info["avg_packet_loss"], 1)),
                            "Jumlah Anchor": info["anchor_count"],
                            "RTO Count": info["rto_count"],
                        })
                    df_probe = pd.DataFrame(probe_rows)

                    def color_probe_status(val):
                        if val == "DOWN":
                            return "background-color: #dc2626; color: #ffffff; font-weight: bold"
                        elif val == "DEGRADED":
                            return "background-color: #d97706; color: #ffffff; font-weight: bold"
                        return "background-color: #059669; color: #ffffff"

                    styled_probe = df_probe.style.map(color_probe_status, subset=["Status"])
                    st.dataframe(styled_probe, use_container_width=True)

            with col_detail:
                st.markdown("#### Detail Semua Anchor Points")
                detail_rows = []
                for r in data["probe_results"]:
                    detail_rows.append({
                        "Host": r.get("host", r.get("ip", "")),
                        "Lokasi": r["nama_lokasi"],
                        "Kecamatan": r["kecamatan"],
                        "Latency (ms)": str(r["latency_ms"]) if r["latency_ms"] >= 0 else "RTO",
                        "Packet Loss (%)": str(round(r["packet_loss_pct"], 1)),
                        "Status": r["status"],
                    })
                df_detail = pd.DataFrame(detail_rows)
                st.dataframe(df_detail, use_container_width=True, height=400)

    # Footer
    st.markdown("---")
    st.markdown(
        '<div class="app-footer">'
        "Lampung Digital Resilience Monitor v2.0 | Real-time OSINT Data | "
        "BMKG API + Google News RSS + ICMP Ping"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
