"""
Social Signal Processor - The "Human Sensor" Module.

Modul ini bertanggung jawab untuk:
1. Mengumpulkan data keluhan REAL dari Google News RSS dan Google Search
2. Memproses keluhan menggunakan NLP pipeline
3. Mengagregasi data per kecamatan untuk scoring
"""

import logging

import pandas as pd
from datetime import datetime, timedelta
from collections import Counter

from modules.scraper import fetch_all_social_signals
from modules.nlp_processor import process_batch

logger = logging.getLogger(__name__)


def fetch_social_signals(**kwargs):
    """
    Mengambil dan memproses sinyal sosial media REAL.
    Sumber: Google News RSS + Google Search scraping.

    Returns:
        list[dict]: Daftar keluhan yang sudah diproses NLP.
    """
    raw_signals = fetch_all_social_signals()
    logger.info("Raw social signals fetched: %d", len(raw_signals))

    processed = process_batch(raw_signals)
    logger.info(
        "Processed signals: %d total, %d digital issues",
        len(processed),
        sum(1 for s in processed if s.get("is_digital_issue")),
    )
    return processed


def aggregate_by_kecamatan(processed_signals):
    """
    Agregasi sinyal per kecamatan.

    Returns:
        dict: {kecamatan: {count, avg_sentiment, providers, severity_max, reports}}
    """
    aggregated = {}

    digital_signals = [s for s in processed_signals if s["is_digital_issue"]]

    for signal in digital_signals:
        kec = signal["primary_location"]
        if kec == "Unknown":
            continue

        if kec not in aggregated:
            aggregated[kec] = {
                "complaint_count": 0,
                "sentiments": [],
                "providers": [],
                "severities": [],
                "latest_reports": [],
            }

        aggregated[kec]["complaint_count"] += 1
        aggregated[kec]["sentiments"].append(signal["sentiment_score"])
        aggregated[kec]["providers"].extend(signal["providers_detected"])
        aggregated[kec]["severities"].append(signal["severity"])
        aggregated[kec]["latest_reports"].append({
            "time": signal["timestamp"],
            "text": signal["original_text"],
            "provider": signal["primary_provider"],
            "severity": signal["severity"],
        })

    # Hitung statistik agregat
    for kec, data in aggregated.items():
        data["avg_sentiment"] = round(
            sum(data["sentiments"]) / len(data["sentiments"]), 2
        ) if data["sentiments"] else 0

        provider_counts = Counter(data["providers"])
        data["top_providers"] = provider_counts.most_common(3)

        data["max_severity"] = (
            "critical" if "critical" in data["severities"]
            else "warning" if "warning" in data["severities"]
            else "normal"
        )

        data["latest_reports"].sort(key=lambda x: x["time"], reverse=True)
        data["latest_reports"] = data["latest_reports"][:5]

        # Cleanup
        del data["sentiments"]
        del data["providers"]
        del data["severities"]

    return aggregated


def get_social_score(kecamatan_aggregation):
    """
    Hitung social score (0-100) per kecamatan.
    0 = sangat buruk, 100 = normal.

    Faktor:
    - Jumlah keluhan (lebih banyak = skor lebih rendah)
    - Rata-rata sentiment (lebih negatif = skor lebih rendah)
    - Severity tertinggi
    """
    scores = {}

    for kec, data in kecamatan_aggregation.items():
        count = data["complaint_count"]
        avg_sent = data["avg_sentiment"]
        severity = data["max_severity"]

        # Base score dari jumlah keluhan (max penalty di 10+ keluhan)
        count_score = max(0, 100 - (count * 15))

        # Sentiment adjustment (-1.0 = -30 poin, 0.0 = 0 poin)
        sentiment_penalty = abs(avg_sent) * 30

        # Severity multiplier
        severity_mult = {"critical": 0.5, "warning": 0.75, "normal": 1.0}
        mult = severity_mult.get(severity, 1.0)

        score = max(0, (count_score - sentiment_penalty) * mult)
        scores[kec] = round(score, 1)

    return scores
