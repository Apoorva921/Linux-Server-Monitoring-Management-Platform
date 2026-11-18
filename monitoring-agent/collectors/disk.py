from typing import Any, Dict, List

import psutil

BYTES_PER_GB = 1024.0 * 1024.0 * 1024.0
IGNORED_FSTYPES = {
    "tmpfs",
    "devtmpfs",
    "squashfs",
    "overlay",
    "proc",
    "sysfs",
    "cgroup",
    "cgroup2",
    "debugfs",
    "tracefs",
    "fusectl",
    "mqueue",
    "hugetlbfs",
    "autofs",
    "devpts",
    "pstore",
    "securityfs",
    "configfs",
}


def collect_disk_metrics() -> Dict[str, Any]:
    """Collect real disk partition utilization, excluding pseudo-filesystems."""
    partitions: List[Dict[str, Any]] = []
    seen_devices = set()
    total_gb = 0.0
    used_gb = 0.0

    for part in psutil.disk_partitions(all=False):
        if part.fstype.lower() in IGNORED_FSTYPES:
            continue
        if part.device.startswith("/dev/loop"):
            continue
        if part.device in seen_devices:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        if usage.total <= 0:
            continue

        seen_devices.add(part.device)
        p_total = round(usage.total / BYTES_PER_GB, 2)
        p_used = round(usage.used / BYTES_PER_GB, 2)
        p_free = round(usage.free / BYTES_PER_GB, 2)
        p_pct = round(float(usage.percent), 2)

        partitions.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype or "unknown",
                "total_gb": p_total,
                "used_gb": p_used,
                "free_gb": p_free,
                "percent": p_pct,
            }
        )
        total_gb += p_total
        used_gb += p_used

    if total_gb <= 0:
        # Fallback to root filesystem
        try:
            root_usage = psutil.disk_usage("/")
            total_gb = round(max(0.01, root_usage.total / BYTES_PER_GB), 2)
            used_gb = round(root_usage.used / BYTES_PER_GB, 2)
            overall_pct = round(float(root_usage.percent), 2)
        except OSError:
            total_gb, used_gb, overall_pct = 1.0, 0.0, 0.0
    else:
        overall_pct = round(min(100.0, (used_gb / total_gb) * 100.0), 2)

    return {
        "disk_percent": overall_pct,
        "disk_used_gb": round(used_gb, 2),
        "disk_total_gb": round(max(0.01, total_gb), 2),
        "disk_partitions": partitions,
    }

