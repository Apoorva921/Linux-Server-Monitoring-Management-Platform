import time
from typing import Any, Dict, Optional

import psutil


class NetworkCollector:
    """
    Collects both cumulative OS network counters (bytes/packets sent & received)
    and computes real-time upload/download throughput (bytes/sec) from deltas.
    """

    def __init__(self) -> None:
        self._prev_sent: Optional[int] = None
        self._prev_recv: Optional[int] = None
        self._prev_ts: Optional[float] = None

    def _detect_primary_interface(self) -> str:
        per_nic = psutil.net_io_counters(pernic=True)
        stats = psutil.net_if_stats()
        candidates = []
        for name, counters in per_nic.items():
            lower = name.lower()
            if lower.startswith(("lo", "docker", "br-", "veth", "virbr")):
                continue
            nic_stat = stats.get(name)
            if nic_stat and not nic_stat.isup:
                continue
            traffic = counters.bytes_sent + counters.bytes_recv
            candidates.append((traffic, name))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return "all"

    def collect(self) -> Dict[str, Any]:
        now = time.monotonic()
        io = psutil.net_io_counters()
        interface = self._detect_primary_interface()

        bytes_sent = int(io.bytes_sent)
        bytes_recv = int(io.bytes_recv)
        packets_sent = int(io.packets_sent)
        packets_recv = int(io.packets_recv)

        upload_bps = 0.0
        download_bps = 0.0
        if self._prev_ts is not None and self._prev_sent is not None and self._prev_recv is not None:
            elapsed = max(0.001, now - self._prev_ts)
            upload_bps = round(max(0.0, (bytes_sent - self._prev_sent) / elapsed), 2)
            download_bps = round(max(0.0, (bytes_recv - self._prev_recv) / elapsed), 2)

        self._prev_sent = bytes_sent
        self._prev_recv = bytes_recv
        self._prev_ts = now

        return {
            "net_bytes_sent": bytes_sent,
            "net_bytes_recv": bytes_recv,
            "net_packets_sent": packets_sent,
            "net_packets_recv": packets_recv,
            "net_interface": interface,
            "net_upload_bps": upload_bps,
            "net_download_bps": download_bps,
        }

