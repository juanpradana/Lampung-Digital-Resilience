"""
Infrastructure Probing Module - The "Anchor Check" Module.

Modul ini bertanggung jawab untuk:
1. Membaca daftar anchor points dari anchors.csv
2. Melakukan ICMP ping REAL ke setiap anchor via subprocess
3. Mengagregasi status per kecamatan
"""

import logging
import os
import platform
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PING_COUNT = 4
PING_TIMEOUT = 5  # detik per host
MAX_WORKERS = 10  # parallel ping threads


def load_anchors():
    """
    Membaca file anchors.csv yang berisi daftar domain/IP anchor points.

    Returns:
        pd.DataFrame: DataFrame dengan kolom Host, Nama_Lokasi, Kecamatan, dll.
    """
    csv_path = os.path.join(BASE_DIR, "data", "anchors.csv")
    return pd.read_csv(csv_path)


def _ping_host(host, count=PING_COUNT, timeout=PING_TIMEOUT):
    """
    Melakukan ICMP ping ke satu host menggunakan subprocess.
    Kompatibel dengan Windows dan Linux.

    Returns:
        dict: {latency_ms, packet_loss_pct, status}
    """
    system = platform.system().lower()

    try:
        if system == "windows":
            cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout * count + 10,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout + result.stderr

        # Parse packet loss
        packet_loss = _parse_packet_loss(output, system)

        # Parse latency (average)
        latency = _parse_latency(output, system)

        if packet_loss >= 100:
            status = "RTO"
            latency = -1
        elif packet_loss > 20 or (latency is not None and latency > 200):
            status = "HIGH_LATENCY"
        else:
            status = "OK"

        return {
            "latency_ms": round(latency, 1) if latency is not None and latency >= 0 else -1,
            "packet_loss_pct": packet_loss,
            "status": status,
        }

    except subprocess.TimeoutExpired:
        logger.warning("Ping timeout untuk %s", host)
        return {"latency_ms": -1, "packet_loss_pct": 100.0, "status": "RTO"}
    except Exception as e:
        logger.error("Ping error untuk %s: %s", host, e)
        return {"latency_ms": -1, "packet_loss_pct": 100.0, "status": "RTO"}


def _parse_packet_loss(output, system):
    """Parse persentase packet loss dari output ping."""
    try:
        if system == "windows":
            # "Lost = 0 (0% loss)" atau "(0% loss)"
            match = re.search(r"\((\d+)%\s*(loss|hilang)\)", output, re.IGNORECASE)
            if match:
                return float(match.group(1))
            # Fallback: cek "Lost = X"
            match = re.search(r"Lost\s*=\s*(\d+)", output, re.IGNORECASE)
            if match:
                lost = int(match.group(1))
                sent_match = re.search(r"Sent\s*=\s*(\d+)", output, re.IGNORECASE)
                sent = int(sent_match.group(1)) if sent_match else PING_COUNT
                return round((lost / sent) * 100, 1) if sent > 0 else 100.0
        else:
            # "4 packets transmitted, 4 received, 0% packet loss"
            match = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", output)
            if match:
                return float(match.group(1))
    except Exception:
        pass
    return 100.0  # Default: assume total loss jika tidak bisa parse


def _parse_latency(output, system):
    """Parse rata-rata latency dari output ping."""
    try:
        if system == "windows":
            # "Average = 25ms"
            match = re.search(r"Average\s*=\s*(\d+)\s*ms", output, re.IGNORECASE)
            if match:
                return float(match.group(1))
            # Fallback: "Rata-rata = 25ms" (Windows Indonesia)
            match = re.search(r"rata-rata\s*=\s*(\d+)\s*ms", output, re.IGNORECASE)
            if match:
                return float(match.group(1))
        else:
            # "rtt min/avg/max/mdev = 10.123/25.456/40.789/10.111 ms"
            match = re.search(r"=\s*[\d.]+/([\d.]+)/", output)
            if match:
                return float(match.group(1))
    except Exception:
        pass
    return None


def probe_anchors():
    """
    Melakukan ping REAL ke semua anchor points secara paralel.

    Returns:
        list[dict]: Hasil ping per anchor point.
    """
    anchors_df = load_anchors()
    results = []

    def _probe_one(row):
        host = row["Host"]
        ping_result = _ping_host(host)
        return {
            "host": host,
            "nama_lokasi": row["Nama_Lokasi"],
            "kecamatan": row["Kecamatan"],
            "kabupaten": row.get("Kabupaten", ""),
            "latency_ms": ping_result["latency_ms"],
            "packet_loss_pct": ping_result["packet_loss_pct"],
            "status": ping_result["status"],
            "timestamp": datetime.now().isoformat(),
        }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_probe_one, row): idx
            for idx, row in anchors_df.iterrows()
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                logger.error("Probe worker error: %s", e)

    logger.info("Infrastructure probe selesai: %d hosts", len(results))
    return results


def aggregate_probe_by_kecamatan(probe_results):
    """
    Agregasi hasil probe per kecamatan.

    Returns:
        dict: {kecamatan: {status, avg_latency, avg_packet_loss, anchor_count, details}}
    """
    aggregated = {}

    for result in probe_results:
        kec = result["kecamatan"]

        if kec not in aggregated:
            aggregated[kec] = {
                "anchors": [],
                "latencies": [],
                "packet_losses": [],
                "statuses": [],
            }

        aggregated[kec]["anchors"].append(result)
        if result["latency_ms"] >= 0:
            aggregated[kec]["latencies"].append(result["latency_ms"])
        aggregated[kec]["packet_losses"].append(result["packet_loss_pct"])
        aggregated[kec]["statuses"].append(result["status"])

    # Hitung statistik
    for kec, data in aggregated.items():
        rto_count = data["statuses"].count("RTO")
        high_lat_count = data["statuses"].count("HIGH_LATENCY")
        total = len(data["statuses"])

        if rto_count == total:
            data["overall_status"] = "DOWN"
        elif rto_count > 0 or high_lat_count > 0:
            data["overall_status"] = "DEGRADED"
        else:
            data["overall_status"] = "OK"

        data["avg_latency"] = round(
            sum(data["latencies"]) / len(data["latencies"]), 1
        ) if data["latencies"] else -1

        data["avg_packet_loss"] = round(
            sum(data["packet_losses"]) / len(data["packet_losses"]), 1
        )

        data["anchor_count"] = total
        data["rto_count"] = rto_count

        # Cleanup raw lists
        del data["latencies"]
        del data["packet_losses"]
        del data["statuses"]

    return aggregated


def get_infra_score(kecamatan_aggregation):
    """
    Hitung infrastructure score (0-100) per kecamatan.
    0 = semua anchor down, 100 = semua normal.
    """
    scores = {}

    for kec, data in kecamatan_aggregation.items():
        status = data["overall_status"]
        avg_loss = data["avg_packet_loss"]
        avg_lat = data["avg_latency"]

        if status == "DOWN":
            scores[kec] = 0.0
        elif status == "DEGRADED":
            # Skor berdasarkan packet loss dan latency
            loss_score = max(0, 100 - avg_loss)
            lat_score = max(0, 100 - (avg_lat / 10)) if avg_lat > 0 else 50
            scores[kec] = round((loss_score + lat_score) / 2, 1)
        else:
            scores[kec] = 100.0

    return scores
