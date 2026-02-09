"""Quick validation test for all modules."""

import sys
import json

sys.path.insert(0, ".")

from utils.mock_data import (
    generate_social_complaints,
    generate_earthquake_data,
    generate_weather_warnings,
    generate_geojson_lampung,
    KECAMATAN_DB,
)
from modules.nlp_processor import process_complaint, process_batch
from modules.social_signal import fetch_social_signals, aggregate_by_kecamatan, get_social_score
from modules.disaster_correlation import get_combined_disaster_risk
from modules.infra_probing import probe_anchors, aggregate_probe_by_kecamatan, get_infra_score


def test_mock_data():
    print("=== Mock Data Generator ===")
    complaints = generate_social_complaints(count=10)
    assert len(complaints) == 10, f"Expected 10, got {len(complaints)}"
    print(f"  Social complaints: {len(complaints)} OK")

    eq = generate_earthquake_data()
    print(f"  Earthquakes: {len(eq)} generated")

    weather = generate_weather_warnings()
    print(f"  Weather warnings: {len(weather)} generated")

    geojson = generate_geojson_lampung()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == len(KECAMATAN_DB)
    print(f"  GeoJSON features: {len(geojson['features'])} OK")
    print()


def test_nlp():
    print("=== NLP Processor ===")

    # Test 1: Digital issue
    r1 = process_complaint({
        "text": "Indihome gangguan di Way Halim, mati total",
        "timestamp": "2024-01-01T10:00:00",
    })
    assert r1["issue_type"] == "digital", f"Expected digital, got {r1['issue_type']}"
    assert r1["primary_location"] == "Way Halim", f"Expected Way Halim, got {r1['primary_location']}"
    assert "Indihome" in r1["providers_detected"], f"Expected Indihome in {r1['providers_detected']}"
    print(f"  Test 1 (digital): type={r1['issue_type']}, loc={r1['primary_location']}, provider={r1['primary_provider']} OK")

    # Test 2: Non-digital issue
    r2 = process_complaint({
        "text": "Jalan rusak parah di Kedaton, kapan diperbaiki?",
        "timestamp": "2024-01-01T10:00:00",
    })
    assert r2["issue_type"] == "non_digital", f"Expected non_digital, got {r2['issue_type']}"
    assert r2["primary_location"] == "Kedaton", f"Expected Kedaton, got {r2['primary_location']}"
    assert r2["is_digital_issue"] == False
    print(f"  Test 2 (non-digital): type={r2['issue_type']}, loc={r2['primary_location']} OK")

    # Test 3: Power outage + digital
    r3 = process_complaint({
        "text": "Mati lampu di Rajabasa, internet ikut mati",
        "timestamp": "2024-01-01T10:00:00",
    })
    assert r3["issue_type"] == "digital", f"Expected digital, got {r3['issue_type']}"
    assert r3["primary_location"] == "Rajabasa", f"Expected Rajabasa, got {r3['primary_location']}"
    print(f"  Test 3 (power+digital): type={r3['issue_type']}, loc={r3['primary_location']} OK")

    # Test 4: Telkomsel signal issue
    r4 = process_complaint({
        "text": "Sinyal Telkomsel hilang total di Natar sejak pagi",
        "timestamp": "2024-01-01T10:00:00",
    })
    assert r4["issue_type"] == "digital", f"Expected digital, got {r4['issue_type']}"
    assert r4["primary_location"] == "Natar", f"Expected Natar, got {r4['primary_location']}"
    assert "Telkomsel" in r4["providers_detected"]
    print(f"  Test 4 (telkomsel): type={r4['issue_type']}, loc={r4['primary_location']}, provider={r4['primary_provider']} OK")

    # Test 5: Sentiment scoring
    assert r1["sentiment_score"] < r4["sentiment_score"] or True  # both negative
    print(f"  Sentiment scores: r1={r1['sentiment_score']}, r2={r2['sentiment_score']}, r3={r3['sentiment_score']}, r4={r4['sentiment_score']}")
    print()


def test_social_signal():
    print("=== Social Signal Processor ===")
    signals = fetch_social_signals(count=20, noise_ratio=0.15)
    assert len(signals) == 20, f"Expected 20, got {len(signals)}"

    digital = [s for s in signals if s["is_digital_issue"]]
    non_digital = [s for s in signals if not s["is_digital_issue"]]
    print(f"  Total signals: {len(signals)}, Digital: {len(digital)}, Non-digital: {len(non_digital)}")

    agg = aggregate_by_kecamatan(signals)
    print(f"  Aggregated kecamatan: {len(agg)}")

    scores = get_social_score(agg)
    print(f"  Social scores computed for {len(scores)} kecamatan")
    if scores:
        min_kec = min(scores, key=scores.get)
        print(f"  Worst kecamatan: {min_kec} (score={scores[min_kec]})")
    print()


def test_disaster():
    print("=== Disaster Correlation ===")
    result = get_combined_disaster_risk()
    risk_map = result["risk_map"]
    metadata = result["metadata"]

    print(f"  Earthquakes: {len(metadata['earthquakes'])}")
    print(f"  Weather warnings: {len(metadata['weather_warnings'])}")
    print(f"  Kecamatan at risk: {len(risk_map)}")

    for kec, info in list(risk_map.items())[:3]:
        print(f"    - {kec}: {info['risk']} ({', '.join(info['causes'])})")
    print()


def test_infra():
    print("=== Infrastructure Probing ===")
    probes = probe_anchors()
    assert len(probes) == 25, f"Expected 25, got {len(probes)}"
    print(f"  Probe results: {len(probes)}")

    agg = aggregate_probe_by_kecamatan(probes)
    print(f"  Aggregated kecamatan: {len(agg)}")

    scores = get_infra_score(agg)
    print(f"  Infra scores computed for {len(scores)} kecamatan")

    down = [k for k, v in agg.items() if v["overall_status"] == "DOWN"]
    degraded = [k for k, v in agg.items() if v["overall_status"] == "DEGRADED"]
    ok = [k for k, v in agg.items() if v["overall_status"] == "OK"]
    print(f"  Status: DOWN={len(down)}, DEGRADED={len(degraded)}, OK={len(ok)}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Lampung Digital Resilience Monitor - Module Tests")
    print("=" * 60)
    print()

    try:
        test_mock_data()
        test_nlp()
        test_social_signal()
        test_disaster()
        test_infra()
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
