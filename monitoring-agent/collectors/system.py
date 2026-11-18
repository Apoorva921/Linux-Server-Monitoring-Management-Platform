import platform
import socket
import time
from pathlib import Path
from typing import Any, Dict

import psutil

from config.settings import AGENT_VERSION


def _read_linux_os_release() -> tuple[str, str]:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return platform.system(), platform.release()

    data: Dict[str, str] = {}
    try:
        for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        return platform.system(), platform.release()

    name = data.get("NAME") or platform.system()
    version = data.get("VERSION") or data.get("VERSION_ID") or platform.release()
    return name, version


def _detect_primary_ip() -> str:
    """Determine primary non-loopback IPv4 address without sending external packets."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        try:
            # connect() on a UDP socket performs route lookup without transmitting data
            sock.connect(("10.255.255.255", 1))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        finally:
            sock.close()
    except OSError:
        pass

    for addrs in psutil.net_if_addrs().values():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                return addr.address
    return "127.0.0.1"


def collect_host_info() -> Dict[str, Any]:
    os_name, os_version = _read_linux_os_release()
    return {
        "hostname": socket.gethostname(),
        "ip_address": _detect_primary_ip(),
        "os_name": os_name[:128],
        "os_version": os_version[:128],
        "kernel_version": platform.release()[:128],
        "architecture": platform.machine()[:64] or "x86_64",
        "cpu_cores": int(psutil.cpu_count(logical=True) or 1),
        "agent_version": AGENT_VERSION,
    }


def collect_uptime_seconds() -> int:
    try:
        return max(0, int(time.time() - psutil.boot_time()))
    except OSError:
        return 0

