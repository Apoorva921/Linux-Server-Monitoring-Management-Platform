import json
import logging
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Matches standard RFC 3164 syslog lines: "Nov 18 22:10:01 host service[123]: message"
SYSLOG_RE = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<source>[^:\[\s]+)(?:\[\d+\])?:\s*(?P<message>.*)$"
)
# Matches ISO-8601 syslog lines: "2026-11-18T17:10:01.123456+00:00 host service[123]: message"
ISO_SYSLOG_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(?P<host>\S+)\s+(?P<source>[^:\[\s]+)(?:\[\d+\])?:\s*(?P<message>.*)$"
)

JOURNAL_PRIORITY_MAP = {
    "0": "CRITICAL",
    "1": "CRITICAL",
    "2": "CRITICAL",
    "3": "ERROR",
    "4": "WARNING",
    "5": "INFO",
    "6": "INFO",
    "7": "DEBUG",
}


def infer_severity(message: str) -> str:
    lower = message.lower()
    if any(k in lower for k in ("panic", "fatal", "critical", "emerg", "alert", "out of memory", "oom-killer")):
        return "CRITICAL"
    if any(k in lower for k in ("error", "failed", "failure", "segfault", "denied", "refused", "exception", "corrupt")):
        return "ERROR"
    if any(k in lower for k in ("warn", "invalid user", "timeout", "deprecated", "retry", "throttl")):
        return "WARNING"
    if any(k in lower for k in ("debug", "trace")):
        return "DEBUG"
    return "INFO"


def parse_syslog_line(raw_line: str, default_source: str, default_host: str) -> Dict[str, Any]:
    line = raw_line.strip()
    now = datetime.now(timezone.utc)

    iso_match = ISO_SYSLOG_RE.match(line)
    if iso_match:
        ts_raw = iso_match.group("ts").replace("Z", "+00:00")
        try:
            ts = datetime.fromisoformat(ts_raw).astimezone(timezone.utc)
        except ValueError:
            ts = now
        msg = iso_match.group("message").strip() or line
        return {
            "timestamp": ts.isoformat(),
            "severity": infer_severity(msg),
            "source": iso_match.group("source")[:128],
            "hostname": iso_match.group("host")[:255],
            "message": msg[:4096],
            "raw_line": line[:4096],
        }

    rfc_match = SYSLOG_RE.match(line)
    if rfc_match:
        try:
            dt_str = f"{now.year} {rfc_match.group('month')} {rfc_match.group('day')} {rfc_match.group('time')}"
            ts = datetime.strptime(dt_str, "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            ts = now
        msg = rfc_match.group("message").strip() or line
        return {
            "timestamp": ts.isoformat(),
            "severity": infer_severity(msg),
            "source": rfc_match.group("source")[:128],
            "hostname": rfc_match.group("host")[:255],
            "message": msg[:4096],
            "raw_line": line[:4096],
        }

    return {
        "timestamp": now.isoformat(),
        "severity": infer_severity(line),
        "source": default_source[:128],
        "hostname": default_host[:255],
        "message": line[:4096],
        "raw_line": line[:4096],
    }


class LogCollector:
    """
    Restricted, read-only Linux log collector for approved sources
    (/var/log/syslog, /var/log/auth.log, and optional journalctl).

    Never attempts privilege escalation or arbitrary command execution.
    """

    def __init__(
        self,
        log_sources: List[str],
        enable_journalctl: bool = True,
        max_lines_per_cycle: int = 100,
    ) -> None:
        self.log_sources = log_sources
        self.enable_journalctl = enable_journalctl
        self.max_lines_per_cycle = max_lines_per_cycle
        self.hostname = socket.gethostname()
        self._file_state: Dict[str, Tuple[int, int]] = {}  # path -> (inode, byte_offset)
        self._warned_paths: Set[str] = set()
        self._last_journal_cursor: Optional[str] = None

    def _read_file_delta(self, path_str: str) -> List[Dict[str, Any]]:
        path = Path(path_str)
        if not path.exists() or not path.is_file():
            return []

        try:
            stat = os.stat(path)
        except PermissionError:
            if path_str not in self._warned_paths:
                logger.warning("Permission denied reading %s (skipping without privilege escalation)", path_str)
                self._warned_paths.add(path_str)
            return []
        except OSError:
            return []

        inode = getattr(stat, "st_ino", 0)
        file_size = stat.st_size
        prev_inode, prev_offset = self._file_state.get(path_str, (-1, -1))

        # On first read, start near the tail (last 16 KB) to avoid flooding historical archives
        if prev_offset == -1:
            offset = max(0, file_size - 16384)
        elif prev_inode != inode or file_size < prev_offset:
            # File was rotated or truncated
            offset = 0
        else:
            offset = prev_offset

        entries: List[Dict[str, Any]] = []
        default_source = path.name
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                lines = []
                for _ in range(self.max_lines_per_cycle):
                    line = f.readline()
                    if not line:
                        break
                    if line.strip():
                        lines.append(line)
                new_offset = f.tell()
            self._file_state[path_str] = (inode, new_offset)
            for ln in lines:
                entries.append(parse_syslog_line(ln, default_source=default_source, default_host=self.hostname))
        except PermissionError:
            if path_str not in self._warned_paths:
                logger.warning("Permission denied opening %s (ensure user is in 'adm' group)", path_str)
                self._warned_paths.add(path_str)
        except OSError as exc:
            logger.debug("Unable to read %s: %s", path_str, exc)

        return entries

    def _read_journalctl(self) -> List[Dict[str, Any]]:
        if not self.enable_journalctl or not shutil.which("journalctl"):
            return []

        cmd = ["journalctl", "--no-pager", "--output=json", "-n", "30"]
        if self._last_journal_cursor:
            cmd.extend(["--after-cursor", self._last_journal_cursor])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                shell=False,  # Explicitly never invoke a shell
            )
        except (OSError, subprocess.SubprocessError):
            return []

        if proc.returncode != 0 or not proc.stdout.strip():
            return []

        entries: List[Dict[str, Any]] = []
        for raw in proc.stdout.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            cursor = obj.get("__CURSOR")
            if cursor:
                self._last_journal_cursor = cursor

            msg = str(obj.get("MESSAGE") or "").strip()
            if not msg:
                continue
            ts_usec = obj.get("__REALTIME_TIMESTAMP")
            if ts_usec:
                try:
                    ts = datetime.fromtimestamp(int(ts_usec) / 1_000_000, tz=timezone.utc).isoformat()
                except (ValueError, OSError):
                    ts = datetime.now(timezone.utc).isoformat()
            else:
                ts = datetime.now(timezone.utc).isoformat()

            priority = str(obj.get("PRIORITY", "6"))
            severity = JOURNAL_PRIORITY_MAP.get(priority, infer_severity(msg))
            source = str(obj.get("SYSLOG_IDENTIFIER") or obj.get("_COMM") or "journald")[:128]
            host = str(obj.get("_HOSTNAME") or self.hostname)[:255]
            entries.append(
                {
                    "timestamp": ts,
                    "severity": severity,
                    "source": source,
                    "hostname": host,
                    "message": msg[:4096],
                    "raw_line": msg[:4096],
                }
            )
        return entries

    def collect(self) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for path_str in self.log_sources:
            collected.extend(self._read_file_delta(path_str))
        if len(collected) < self.max_lines_per_cycle:
            collected.extend(self._read_journalctl())
        return collected[: self.max_lines_per_cycle]

