"""
Data Store - Server-Side Background Data Fetcher.

Modul ini bertanggung jawab untuk:
1. Menyimpan data hasil fetch di memory (thread-safe)
2. Menjalankan background thread yang fetch data secara periodik
3. Client hanya membaca dari cache, TIDAK pernah trigger fetch

Pattern: Singleton + Background Scheduler
- Mencegah spam traffic dari client
- Data selalu fresh sesuai interval yang dikonfigurasi
- Thread-safe untuk multi-session Streamlit
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Default refresh interval dalam detik (5 menit)
DEFAULT_REFRESH_INTERVAL = 300


class DataStore:
    """
    Singleton data store dengan background auto-refresh.

    Data di-fetch oleh background thread setiap `refresh_interval` detik.
    Client memanggil `get_data()` untuk membaca data dari cache.
    Tidak ada fetch yang dipicu oleh client request.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, refresh_interval=DEFAULT_REFRESH_INTERVAL):
        if self._initialized:
            return
        self._initialized = True

        self._refresh_interval = refresh_interval
        self._data = None
        self._data_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._is_fetching = False
        self._last_refresh = None
        self._next_refresh = None
        self._fetch_count = 0
        self._last_error = None

        # Fetch pertama kali secara sinkron agar data langsung tersedia
        self._do_fetch()

        # Jalankan background thread untuk fetch periodik
        self._thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="DataStore-BackgroundFetcher",
        )
        self._thread.start()
        logger.info(
            "DataStore initialized. Refresh interval: %ds. Background thread started.",
            self._refresh_interval,
        )

    def _do_fetch(self):
        """
        Eksekusi fetch data dari semua modul.
        Dipanggil oleh background thread, BUKAN oleh client.
        """
        # Lazy import untuk menghindari circular dependency
        from modules.social_signal import (
            fetch_social_signals,
            aggregate_by_kecamatan,
            get_social_score,
        )
        from modules.disaster_correlation import get_combined_disaster_risk
        from modules.infra_probing import (
            probe_anchors,
            aggregate_probe_by_kecamatan,
            get_infra_score,
        )

        self._is_fetching = True
        fetch_start = time.monotonic()
        logger.info("DataStore: Starting data fetch #%d...", self._fetch_count + 1)

        try:
            # Module A: Social Signals
            social_signals = fetch_social_signals()
            social_agg = aggregate_by_kecamatan(social_signals)
            social_scores = get_social_score(social_agg)

            # Module B: Disaster Correlation
            disaster_data = get_combined_disaster_risk()

            # Module C: Infrastructure Probing
            probe_results = probe_anchors()
            probe_agg = aggregate_probe_by_kecamatan(probe_results)
            infra_scores = get_infra_score(probe_agg)

            new_data = {
                "social_signals": social_signals,
                "social_agg": social_agg,
                "social_scores": social_scores,
                "disaster_data": disaster_data,
                "probe_results": probe_results,
                "probe_agg": probe_agg,
                "infra_scores": infra_scores,
            }

            # Atomic swap — client tidak pernah melihat data setengah jadi
            with self._data_lock:
                self._data = new_data
                self._last_refresh = datetime.now(timezone.utc)
                self._next_refresh = self._last_refresh + timedelta(
                    seconds=self._refresh_interval
                )
                self._fetch_count += 1
                self._last_error = None

            elapsed = time.monotonic() - fetch_start
            logger.info(
                "DataStore: Fetch #%d completed in %.1fs. Next refresh at %s",
                self._fetch_count,
                elapsed,
                self._next_refresh.strftime("%H:%M:%S UTC"),
            )

        except Exception as e:
            self._last_error = str(e)
            logger.error("DataStore: Fetch failed: %s", e, exc_info=True)
        finally:
            self._is_fetching = False

    def _background_loop(self):
        """Background loop yang fetch data setiap `refresh_interval` detik."""
        while not self._stop_event.is_set():
            # Tunggu interval, tapi bisa di-interrupt oleh stop_event
            self._stop_event.wait(timeout=self._refresh_interval)
            if self._stop_event.is_set():
                break
            self._do_fetch()

        logger.info("DataStore: Background thread stopped.")

    def get_data(self):
        """
        Ambil data terbaru dari cache. Thread-safe.
        TIDAK pernah trigger fetch — hanya baca dari memory.

        Returns:
            dict | None: Data terbaru, atau None jika belum ada data.
        """
        with self._data_lock:
            return self._data

    def get_status(self):
        """
        Ambil metadata status refresh.

        Returns:
            dict: {
                last_refresh, next_refresh, is_fetching,
                fetch_count, refresh_interval, last_error
            }
        """
        with self._data_lock:
            return {
                "last_refresh": self._last_refresh,
                "next_refresh": self._next_refresh,
                "is_fetching": self._is_fetching,
                "fetch_count": self._fetch_count,
                "refresh_interval": self._refresh_interval,
                "last_error": self._last_error,
            }

    def set_refresh_interval(self, seconds):
        """Ubah interval refresh (berlaku mulai cycle berikutnya)."""
        self._refresh_interval = max(60, seconds)  # Minimum 1 menit
        logger.info("DataStore: Refresh interval changed to %ds", self._refresh_interval)

    def force_refresh(self):
        """
        Paksa refresh data sekarang (dari background thread baru).
        Berguna untuk admin/manual trigger, tapi BUKAN dari client biasa.
        """
        if self._is_fetching:
            logger.warning("DataStore: Fetch already in progress, skipping force refresh.")
            return
        thread = threading.Thread(
            target=self._do_fetch,
            daemon=True,
            name="DataStore-ForceRefresh",
        )
        thread.start()

    def stop(self):
        """Hentikan background thread."""
        self._stop_event.set()
        logger.info("DataStore: Stop signal sent.")
