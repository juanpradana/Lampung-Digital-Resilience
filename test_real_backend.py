"""
Test suite untuk real data backend.
Memverifikasi bahwa semua modul mengambil data REAL, bukan dummy.
"""

import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, ".")


def test_bmkg_client():
    print("=" * 60)
    print("TEST 1: BMKG Client (Real Earthquake Data)")
    print("=" * 60)

    from modules.bmkg_client import fetch_all_earthquakes, fetch_weather_warnings_lampung

    earthquakes = fetch_all_earthquakes()
    print(f"  Gempa ditemukan: {len(earthquakes)}")
    assert len(earthquakes) > 0, "Seharusnya ada data gempa dari BMKG"

    eq = earthquakes[0]
    print(f"  Gempa terbaru: M{eq['magnitude']} - {eq['location']}")
    print(f"    Timestamp: {eq['timestamp']}")
    print(f"    Koordinat: ({eq['latitude']}, {eq['longitude']})")
    print(f"    Kedalaman: {eq['depth_km']} km")
    print(f"    Source: {eq['source']}")

    assert eq["magnitude"] > 0, "Magnitude harus > 0"
    assert eq["latitude"] is not None, "Latitude harus ada"
    assert eq["longitude"] is not None, "Longitude harus ada"

    warnings = fetch_weather_warnings_lampung()
    print(f"  Peringatan cuaca: {len(warnings)}")
    print()
    return True


def test_scraper():
    print("=" * 60)
    print("TEST 2: Scraper (Real Google News RSS + Google Search)")
    print("=" * 60)

    from modules.scraper import fetch_google_news_rss, fetch_all_social_signals

    # Test RSS saja dulu (lebih reliable)
    rss_results = fetch_google_news_rss(
        queries=["gangguan internet Lampung", "indihome down Lampung"],
        max_per_query=5,
    )
    print(f"  Google News RSS entries: {len(rss_results)}")
    assert len(rss_results) > 0, "Seharusnya ada hasil dari Google News RSS"

    entry = rss_results[0]
    print(f"  Contoh entry:")
    print(f"    Title: {entry['title'][:80]}")
    print(f"    Source: {entry['source_name']}")
    print(f"    Timestamp: {entry['timestamp']}")
    print(f"    Text (50 char): {entry['text'][:50]}...")

    assert entry["text"], "Text tidak boleh kosong"
    assert entry["timestamp"], "Timestamp tidak boleh kosong"

    # Test full pipeline
    all_signals = fetch_all_social_signals()
    print(f"  Total sinyal sosial (semua sumber): {len(all_signals)}")
    print()
    return True


def test_infra_probing():
    print("=" * 60)
    print("TEST 3: Infrastructure Probing (Real ICMP Ping)")
    print("=" * 60)

    from modules.infra_probing import load_anchors, probe_anchors

    anchors = load_anchors()
    print(f"  Anchor points loaded: {len(anchors)}")
    print(f"  Kolom: {list(anchors.columns)}")

    # Ping hanya 3 host pertama untuk test cepat
    from modules.infra_probing import _ping_host
    test_hosts = anchors["Host"].head(3).tolist()

    for host in test_hosts:
        result = _ping_host(host, count=2, timeout=3)
        status_icon = (
            "OK" if result["status"] == "OK"
            else "WARN" if result["status"] == "HIGH_LATENCY"
            else "FAIL"
        )
        lat_str = f"{result['latency_ms']}ms" if result["latency_ms"] >= 0 else "RTO"
        print(f"  [{status_icon}] {host}: {lat_str} | Loss: {result['packet_loss_pct']}%")

    print()
    return True


def test_social_signal_pipeline():
    print("=" * 60)
    print("TEST 4: Social Signal Pipeline (Scraper -> NLP -> Aggregation)")
    print("=" * 60)

    from modules.social_signal import fetch_social_signals, aggregate_by_kecamatan, get_social_score

    signals = fetch_social_signals()
    print(f"  Total processed signals: {len(signals)}")

    digital = [s for s in signals if s.get("is_digital_issue")]
    non_digital = [s for s in signals if not s.get("is_digital_issue")]
    print(f"  Digital issues: {len(digital)}")
    print(f"  Non-digital: {len(non_digital)}")

    if digital:
        sample = digital[0]
        print(f"  Contoh digital signal:")
        print(f"    Text: {sample['original_text'][:80]}...")
        print(f"    Location: {sample['primary_location']}")
        print(f"    Provider: {sample['primary_provider']}")
        print(f"    Severity: {sample['severity']}")
        print(f"    Sentiment: {sample['sentiment_score']}")

    agg = aggregate_by_kecamatan(signals)
    print(f"  Kecamatan dengan keluhan: {len(agg)}")

    scores = get_social_score(agg)
    print(f"  Social scores computed: {len(scores)}")
    if scores:
        worst = min(scores, key=scores.get)
        print(f"  Worst kecamatan: {worst} (score={scores[worst]})")

    print()
    return True


def test_disaster_correlation():
    print("=" * 60)
    print("TEST 5: Disaster Correlation (Real BMKG -> Risk Map)")
    print("=" * 60)

    from modules.disaster_correlation import get_combined_disaster_risk

    result = get_combined_disaster_risk()
    risk_map = result["risk_map"]
    metadata = result["metadata"]

    print(f"  Gempa dari BMKG: {len(metadata['earthquakes'])}")
    print(f"  Peringatan cuaca: {len(metadata['weather_warnings'])}")
    print(f"  Kecamatan at risk: {len(risk_map)}")

    for kec, info in list(risk_map.items())[:5]:
        print(f"    - {kec}: {info['risk']} ({', '.join(info['causes'])})")

    print()
    return True


if __name__ == "__main__":
    print()
    print("*" * 60)
    print("  LAMPUNG DIGITAL RESILIENCE - REAL BACKEND TESTS")
    print("*" * 60)
    print()

    results = {}
    tests = [
        ("BMKG Client", test_bmkg_client),
        ("Scraper", test_scraper),
        ("Infra Probing", test_infra_probing),
        ("Social Signal Pipeline", test_social_signal_pipeline),
        ("Disaster Correlation", test_disaster_correlation),
    ]

    for name, test_fn in tests:
        try:
            passed = test_fn()
            results[name] = "PASS" if passed else "FAIL"
        except Exception as e:
            results[name] = f"ERROR: {e}"
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, status in results.items():
        icon = "PASS" if status == "PASS" else "FAIL"
        if icon == "FAIL":
            all_pass = False
        print(f"  [{icon}] {name}: {status}")

    print()
    if all_pass:
        print("ALL TESTS PASSED - Real data backend is working!")
    else:
        print("SOME TESTS FAILED - Check errors above.")

    sys.exit(0 if all_pass else 1)
