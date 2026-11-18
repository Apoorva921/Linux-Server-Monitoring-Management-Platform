import os
from pathlib import Path
from typing import Dict

import psutil


def _read_proc_loadavg() -> tuple[float, float, float]:
    """Read Linux load averages via os.getloadavg() or /proc/loadavg."""
    if hasattr(os, "getloadavg"):
        try:
            l1, l5, l15 = os.getloadavg()
            return round(l1, 2), round(l5, 2), round(l15, 2)
        except OSError:
            pass
    proc_path = Path("/proc/loadavg")
    if proc_path.exists():
        try:
            parts = proc_path.read_text(encoding="utf-8").strip().split()
            return round(float(parts[0]), 2), round(float(parts[1]), 2), round(float(parts[2]), 2)
        except (OSError, ValueError, IndexError):
            pass
    return 0.0, 0.0, 0.0


def collect_cpu_metrics() -> Dict[str, float]:
    """Collect overall CPU percentage, time breakdowns, and system load averages."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    times_pct = psutil.cpu_times_percent(interval=None)
    load_1m, load_5m, load_15m = _read_proc_loadavg()

    return {
        "cpu_percent": round(float(cpu_percent), 2),
        "cpu_user": round(float(getattr(times_pct, "user", 0.0)), 2),
        "cpu_system": round(float(getattr(times_pct, "system", 0.0)), 2),
        "cpu_iowait": round(float(getattr(times_pct, "iowait", 0.0)), 2),
        "load_1m": load_1m,
        "load_5m": load_5m,
        "load_15m": load_15m,
    }

