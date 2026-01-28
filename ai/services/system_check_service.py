from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import psutil


class SystemCheckService:
    def build_report(self, birth_time: Optional[datetime]) -> str:
        system_stats = self._build_system_stats(birth_time)
        host_stats = self._build_host_stats()
        return system_stats + host_stats

    @staticmethod
    def _build_system_stats(birth_time: Optional[datetime]) -> str:
        uptime_str = "unknown"
        if birth_time:
            uptime_seconds = (datetime.now(timezone.utc) - birth_time).total_seconds()
            uptime_hours = uptime_seconds / 3600
            if uptime_hours < 1:
                uptime_str = f"{int(uptime_seconds / 60)} minutes"
            elif uptime_hours < 24:
                uptime_str = f"{uptime_hours:.1f} hours"
            else:
                uptime_str = f"{uptime_hours / 24:.1f} days"

        return "🤖 SYSTEM (My Body):\n" f"- Uptime: {uptime_str}"

    @staticmethod
    def _build_host_stats() -> str:
        cpu_temp = None
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
        except (OSError, ValueError):
            cpu_temp = None

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        temp_str = f"{cpu_temp:.1f}°C" if cpu_temp else "N/A"

        return (
            "\n\n"
            "🏠 HOST (My Home):\n"
            "- Platform: Raspberry Pi 5\n"
            "- Location: Argentina\n"
            f"- CPU: {cpu_count} cores @ {cpu_percent:.1f}% usage\n"
            f"- Temperature: {temp_str}\n"
            f"- Memory: {int(mem.used / 1024 / 1024 / 1024)} GB / "
            f"{int(mem.total / 1024 / 1024 / 1024)} GB ({mem.percent:.1f}% used)\n"
            f"- Disk: {int(disk.used / 1024 / 1024 / 1024)} GB / "
            f"{int(disk.total / 1024 / 1024 / 1024)} GB ({disk.percent:.1f}% used)"
        )
