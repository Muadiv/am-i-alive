from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psutil


class SystemCheckService:
    def build_report(self, birth_time: Optional[datetime]) -> str:
        system_stats = self._build_system_stats(birth_time)
        host_stats = self._build_host_stats()
        return system_stats + host_stats

    def build_process_report(self, limit: int = 5) -> str:
        processes: list[tuple[float, int, str]] = []
        for proc in psutil.process_iter(attrs=["pid", "name", "memory_percent"]):
            try:
                info = proc.info
                pid = int(info.get("pid", 0))
                name = str(info.get("name", "unknown"))
                mem_pct = float(info.get("memory_percent", 0.0) or 0.0)
                processes.append((mem_pct, pid, name))
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, TypeError):
                continue

        processes.sort(reverse=True)
        top = processes[: max(1, limit)]

        lines = ["🧩 PROCESS SNAPSHOT (Top memory users):"]
        if not top:
            lines.append("- Unable to read process list.")
            return "\n".join(lines)

        for mem_pct, pid, name in top:
            lines.append(f"- PID {pid}: {name} ({mem_pct:.1f}% RAM)")

        return "\n".join(lines)

    def build_disk_cleanup_report(self) -> str:
        targets = [
            "/var/log",
            "/var/tmp",
            "/tmp",
            "/var/lib/am-i-alive/data",
            "/var/lib/am-i-alive/memories",
            "/var/lib/am-i-alive/credits",
        ]

        lines = ["🧹 DISK CLEANUP SCAN (no deletions performed):"]
        for target in targets:
            path = Path(target)
            if not path.exists():
                lines.append(f"- {target}: not found")
                continue
            size_bytes, truncated = self._dir_size(path)
            size_label = self._format_bytes(size_bytes)
            suffix = " (partial)" if truncated else ""
            lines.append(f"- {target}: {size_label}{suffix}")

        lines.append("- Suggested: rotate logs or clear temp files if disk usage is high.")
        return "\n".join(lines)

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

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        if size_bytes < 1024**3:
            return f"{size_bytes / 1024**2:.1f} MB"
        return f"{size_bytes / 1024**3:.2f} GB"

    @staticmethod
    def _dir_size(path: Path, max_entries: int = 5000) -> tuple[int, bool]:
        total = 0
        counted = 0
        truncated = False
        for root, _dirs, files in os.walk(path):
            for filename in files:
                try:
                    file_path = Path(root) / filename
                    total += file_path.stat().st_size
                    counted += 1
                    if counted >= max_entries:
                        truncated = True
                        return total, truncated
                except (OSError, ValueError):
                    continue
        return total, truncated
