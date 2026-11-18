import json
import urllib.request

LOGIN_URL = "https://sentinelops-xp4p.onrender.com/api/auth/login"
SERVERS_URL = "https://sentinelops-xp4p.onrender.com/api/servers"
SUMMARY_URL = "https://sentinelops-xp4p.onrender.com/api/dashboard/summary"

headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

# Login
login_req = urllib.request.Request(
    LOGIN_URL,
    data=json.dumps({"username": "admin", "password": "Admin@SentinelOps123!"}).encode(),
    headers=headers,
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode())["access_token"]
print("Authentication successful!")

auth_headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}

# Dashboard summary
summary_req = urllib.request.Request(SUMMARY_URL, headers=auth_headers)
with urllib.request.urlopen(summary_req) as resp:
    summary = json.loads(resp.read().decode())
print("Dashboard summary:")
print(f"  Total servers: {summary.get('total_servers')}")
print(f"  Online: {summary.get('online_servers')}")
print(f"  Warning: {summary.get('warning_servers')}")
print(f"  Critical: {summary.get('critical_servers')}")
print(f"  Offline: {summary.get('offline_servers')}")
print(f"  Avg CPU: {summary.get('avg_cpu_percent')}%")
print(f"  Avg Memory: {summary.get('avg_memory_percent')}%")
print(f"  Avg Disk: {summary.get('avg_disk_percent')}%")

# List servers
srv_req = urllib.request.Request(SERVERS_URL, headers=auth_headers)
with urllib.request.urlopen(srv_req) as resp:
    servers = json.loads(resp.read().decode())
print(f"\nServers registered ({servers['total']}):")
for s in servers["items"]:
    print(f"  • {s['hostname']} ({s['display_name']}) - Status: {s['status']}, Health: {s['health_score']}/100, OS: {s['os_name']}")
