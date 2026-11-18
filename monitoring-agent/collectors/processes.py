from typing import Any, Dict, List

import psutil


def collect_process_metrics(max_processes: int = 30) -> Dict[str, Any]:
    """
    Collect read-only snapshot of running processes sorted by CPU & memory utilization.
    Process termination is intentionally unsupported.
    """
    processes: List[Dict[str, Any]] = []
    total_count = 0

    for proc in psutil.process_iter(
        attrs=["pid", "name", "cpu_percent", "memory_percent", "username", "status"]
    ):
        total_count += 1
        try:
            info = proc.info
            cpu_val = float(info.get("cpu_percent") or 0.0)
            mem_val = min(100.0, max(0.0, float(info.get("memory_percent") or 0.0)))
            processes.append(
                {
                    "pid": int(info.get("pid") or 0),
                    "name": str(info.get("name") or "unknown")[:255],
                    "cpu_percent": round(max(0.0, cpu_val), 2),
                    "memory_percent": round(mem_val, 2),
                    "username": str(info.get("username") or "unknown")[:128],
                    "status": str(info.get("status") or "unknown")[:64],
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(key=lambda p: (p["cpu_percent"], p["memory_percent"]), reverse=True)
    return {
        "process_count": total_count,
        "top_processes": processes[:max_processes],
    }

