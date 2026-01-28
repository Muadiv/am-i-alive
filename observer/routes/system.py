import subprocess
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter

from .. import database as db

router = APIRouter()


@router.get("/api/system/stats")
async def get_system_stats():
    """Return current system statistics."""
    cpu_temp = "unknown"
    try:
        temp = subprocess.check_output(["vcgencmd", "measure_temp"], timeout=2).decode()
        cpu_temp = temp.replace("temp=", "").replace("'C", "").strip()
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
                cpu_temp = f"{float(temp_file.read().strip()) / 1000.0:.1f}"
        except Exception:
            cpu_temp = "unknown"

    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage("/app")
    except Exception:
        disk = psutil.disk_usage("/")

    state = await db.get_current_state()
    birth_time = state.get("birth_time")
    uptime_seconds = 0
    if birth_time:
        try:
            birth_dt = datetime.fromisoformat(birth_time) if isinstance(birth_time, str) else birth_time
            uptime_seconds = max(0, int((datetime.now(timezone.utc) - birth_dt).total_seconds()))
        except Exception:
            uptime_seconds = 0

    return {
        "temperature": cpu_temp,
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "uptime_seconds": uptime_seconds,
        "last_seen": state.get("last_seen"),
    }
