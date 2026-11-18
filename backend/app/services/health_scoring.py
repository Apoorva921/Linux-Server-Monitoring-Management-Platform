from typing import Any, Dict, List


def _linear_penalty(value: float, start: float, mid: float, high: float, mid_pts: float, max_pts: float) -> float:
    """Piecewise-linear penalty curve between start -> mid -> high."""
    if value <= start:
        return 0.0
    if value <= mid:
        ratio = (value - start) / max(mid - start, 1e-6)
        return round(ratio * mid_pts, 2)
    if value < high:
        ratio = (value - mid) / max(high - mid, 1e-6)
        return round(mid_pts + ratio * (max_pts - mid_pts), 2)
    return float(max_pts)


def calculate_health_score(
    *,
    is_online: bool,
    cpu_percent: float,
    memory_percent: float,
    disk_percent: float,
    active_critical_alerts: int = 0,
    active_warning_alerts: int = 0,
) -> Dict[str, Any]:
    """
    Deterministic, transparent server health scoring engine (0-100).

    Weights:
      - Availability: offline server immediately scores 0.
      - CPU utilization: up to -30 pts (starts deducting above 50%).
      - Memory utilization: up to -25 pts (starts deducting above 60%).
      - Disk utilization: up to -25 pts (starts deducting above 70%).
      - Active alerts: -8 per critical alert, -3 per warning alert (capped at -20 pts).
    """
    if not is_online:
        return {
            "score": 0.0,
            "status": "offline",
            "summary": "Server is offline because no heartbeat has been received within the timeout window.",
            "deductions": [
                {
                    "factor": "Availability",
                    "value": "Offline",
                    "impact": -100.0,
                    "reason": "Heartbeat timeout exceeded; agent is unreachable.",
                }
            ],
        }

    deductions: List[Dict[str, Any]] = []
    score = 100.0

    # 1. CPU penalty (max 30)
    cpu_penalty = _linear_penalty(cpu_percent, start=50.0, mid=75.0, high=95.0, mid_pts=15.0, max_pts=30.0)
    if cpu_penalty > 0:
        score -= cpu_penalty
        deductions.append(
            {
                "factor": "CPU Utilization",
                "value": f"{cpu_percent:.1f}%",
                "impact": -cpu_penalty,
                "reason": (
                    "Sustained high CPU load degrades response times."
                    if cpu_percent >= 75.0
                    else "Elevated CPU usage above 50% baseline."
                ),
            }
        )

    # 2. Memory penalty (max 25)
    mem_penalty = _linear_penalty(memory_percent, start=60.0, mid=80.0, high=95.0, mid_pts=12.0, max_pts=25.0)
    if mem_penalty > 0:
        score -= mem_penalty
        deductions.append(
            {
                "factor": "Memory Utilization",
                "value": f"{memory_percent:.1f}%",
                "impact": -mem_penalty,
                "reason": (
                    "High memory pressure risks OOM kills or heavy swapping."
                    if memory_percent >= 80.0
                    else "Memory usage above 60% baseline."
                ),
            }
        )

    # 3. Disk penalty (max 25)
    disk_penalty = _linear_penalty(disk_percent, start=70.0, mid=80.0, high=95.0, mid_pts=12.0, max_pts=25.0)
    if disk_penalty > 0:
        score -= disk_penalty
        deductions.append(
            {
                "factor": "Disk Utilization",
                "value": f"{disk_percent:.1f}%",
                "impact": -disk_penalty,
                "reason": (
                    "Low available disk space can halt logging and database writes."
                    if disk_percent >= 80.0
                    else "Disk utilization approaching 80% warning threshold."
                ),
            }
        )

    # 4. Active alert penalty (max 20)
    alert_penalty = min(20.0, active_critical_alerts * 8.0 + active_warning_alerts * 3.0)
    if alert_penalty > 0:
        score -= alert_penalty
        deductions.append(
            {
                "factor": "Active Alerts",
                "value": f"{active_critical_alerts} critical, {active_warning_alerts} warning",
                "impact": -alert_penalty,
                "reason": "Unresolved threshold alerts actively impacting operational health.",
            }
        )

    score = round(max(0.0, min(100.0, score)), 1)

    # Determine status consistently with score and active alerts
    if active_critical_alerts > 0 or score < 55.0:
        status = "critical"
    elif active_warning_alerts > 0 or score < 80.0:
        status = "warning"
    else:
        status = "healthy"

    if not deductions:
        summary = "All monitored resources (CPU, memory, disk) are within healthy operating ranges with zero active alerts."
    else:
        top_factors = ", ".join(d["factor"] for d in deductions[:3])
        summary = f"Health score is {score}/100 ({status.upper()}). Deductions from: {top_factors}."

    return {
        "score": score,
        "status": status,
        "summary": summary,
        "deductions": deductions,
    }

