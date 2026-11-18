import sys
import time
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from collectors.cpu import collect_cpu_metrics  # noqa: E402
from collectors.disk import collect_disk_metrics  # noqa: E402
from collectors.logs import LogCollector, infer_severity, parse_syslog_line  # noqa: E402
from collectors.memory import collect_memory_metrics  # noqa: E402
from collectors.network import NetworkCollector  # noqa: E402
from collectors.processes import collect_process_metrics  # noqa: E402
from collectors.system import collect_host_info, collect_uptime_seconds  # noqa: E402


def test_real_system_collectors():
    cpu = collect_cpu_metrics()
    assert 0.0 <= cpu["cpu_percent"] <= 100.0
    assert cpu["load_1m"] >= 0.0

    mem = collect_memory_metrics()
    assert 0.0 <= mem["memory_percent"] <= 100.0
    assert mem["memory_total_mb"] > 0.0

    disk = collect_disk_metrics()
    assert 0.0 <= disk["disk_percent"] <= 100.0
    assert disk["disk_total_gb"] > 0.0

    net_col = NetworkCollector()
    first = net_col.collect()
    time.sleep(0.05)
    second = net_col.collect()
    assert first["net_bytes_sent"] >= 0
    assert second["net_upload_bps"] >= 0.0
    assert second["net_download_bps"] >= 0.0

    procs = collect_process_metrics(max_processes=10)
    assert procs["process_count"] > 0
    assert len(procs["top_processes"]) <= 10

    host = collect_host_info()
    assert host["hostname"]
    assert host["cpu_cores"] >= 1
    assert collect_uptime_seconds() >= 0


def test_syslog_parser_and_incremental_log_tailing(tmp_path):
    assert infer_severity("Out of memory: Killed process 99") == "CRITICAL"
    assert infer_severity("Failed password for root from 1.2.3.4") == "ERROR"
    assert infer_severity("Invalid user test from 1.2.3.4") == "WARNING"
    assert infer_severity("Started nginx service") == "INFO"

    parsed = parse_syslog_line(
        "Nov 18 22:10:01 web-01 sshd[1234]: Failed password for root from 10.0.0.5",
        default_source="auth.log",
        default_host="web-01",
    )
    assert parsed["source"] == "sshd"
    assert parsed["hostname"] == "web-01"
    assert parsed["severity"] == "ERROR"

    log_file = tmp_path / "syslog"
    log_file.write_text("Nov 18 22:10:01 host1 kernel: Initial boot info\n", encoding="utf-8")

    collector = LogCollector(log_sources=[str(log_file)], enable_journalctl=False)
    batch1 = collector.collect()
    assert len(batch1) == 1
    assert batch1[0]["source"] == "kernel"

    # Second read with no new lines returns empty (no duplicates)
    assert collector.collect() == []

    # Append a new line -> only new line returned
    with log_file.open("a", encoding="utf-8") as f:
        f.write("Nov 18 22:10:06 host1 nginx[55]: error upstream timed out\n")
    batch2 = collector.collect()
    assert len(batch2) == 1
    assert batch2[0]["severity"] == "ERROR"

