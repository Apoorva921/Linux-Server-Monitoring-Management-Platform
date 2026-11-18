from typing import Dict

import psutil

BYTES_PER_MB = 1024.0 * 1024.0


def collect_memory_metrics() -> Dict[str, float]:
    """Collect RAM and swap utilization in megabytes and percentage."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "memory_percent": round(float(vm.percent), 2),
        "memory_used_mb": round(float(vm.used) / BYTES_PER_MB, 2),
        "memory_available_mb": round(float(vm.available) / BYTES_PER_MB, 2),
        "memory_total_mb": round(max(1.0, float(vm.total) / BYTES_PER_MB), 2),
        "swap_percent": round(float(swap.percent), 2),
    }

