from __future__ import annotations

import os
from typing import Optional

from ..logging_config import logger

from ..logging_config import logger
from ..brain_shared import OBSERVER_URL, WEATHER_LAT, WEATHER_LON
from ..services.health_check_service import HealthCheckService
from ..services.system_check_service import SystemCheckService
from ..services.system_stats_service import SystemStatsService
from ..services.twitter_service import get_twitter_status
from ..services.weather_service import WeatherService


class BrainActionMixin:
    async def check_budget(self) -> str:
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.check_budget()

    async def list_available_models(self) -> str:
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.list_available_models(self.current_model)

    async def check_model_health(self) -> str:
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.check_model_health(self.current_model, self.send_message)

    async def switch_model(self, model_id: str) -> str:
        if not self.budget_service:
            return "❌ Budget service not initialized"
        identity_name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
        result, new_model = await self.budget_service.switch_model(
            self.current_model,
            model_id,
            self.life_number,
            identity_name,
        )
        if new_model is not None:
            self.current_model = new_model
        return result

    async def post_to_x(self, content: str) -> str:
        return await self.twitter_service.post(content, self.report_activity)

    async def post_to_telegram(self, content: str) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.post_to_telegram(content)

    async def write_blog_post(self, title: str, content: str, tags: list[str] | None = None) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        content = self._prepend_thread(content)
        result = await self.action_handler.write_blog_post(title, content, tags)
        if result.startswith("✅"):
            self.thread_state.set_thread(title, content, self.current_topic)
            self.thread_state.save(self.thread_state_path)
        return result

    async def check_system_stats(self) -> str:
        stats = await self.fetch_system_stats()
        service = SystemStatsService(self.http_client, OBSERVER_URL) if self.http_client else None
        result = service.build_vital_signs_report(stats) if service else "I couldn't feel my body right now."
        await self.report_activity("system_stats_checked", "Checked system stats via Observer")
        return result

    async def check_health(self) -> str:
        if not self.http_client:
            return "❌ Health check unavailable."
        stats_service = SystemStatsService(self.http_client, OBSERVER_URL)
        health_service = HealthCheckService(
            stats_service,
            self.budget_service,
            self.current_model,
            self.send_message,
        )
        report = await health_service.build_report()
        await self.report_activity("health_check", "Ran combined health check")
        return report

    async def check_weather(self) -> str:
        if not self.http_client:
            return "❌ Weather check unavailable."
        service = WeatherService(self.http_client, WEATHER_LAT, WEATHER_LON)
        data = await service.fetch_weather()
        report = service.build_report(data)
        await self.report_activity("weather_checked", "Checked local weather")
        return report

    async def check_system(self) -> str:
        try:
            service = SystemCheckService()
            result = service.build_report(self.birth_time)
            await self.report_activity("system_check", "Checked vital signs")
            logger.info("[SYSTEM] ✅ System check complete")
            return result
        except Exception as e:
            logger.error(f"[SYSTEM] ❌ Failed to check system: {e}")
            return f"❌ Failed to check system: {str(e)[:200]}"

    async def check_processes(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_processes()

    async def check_disk_cleanup(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_disk_cleanup()

    async def check_services(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_services()

    async def check_logs(self, service: str, lines: int = 50) -> str:
        service_checker = SystemCheckService()
        report = service_checker.build_log_report(service, lines)
        await self.report_activity("log_check", f"Checked logs for {service}")
        return report

    def check_twitter_status_action(self) -> str:
        return get_twitter_status()

    async def check_votes(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_votes()

    async def read_messages(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.read_messages()

    async def check_state_internal(self) -> str:
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_state()

    def read_file(self, path: str) -> str:
        return self.sandbox_service.read_file(path)

    def write_file(self, path: str, content: str) -> str:
        return self.sandbox_service.write_file(path, content)

    def run_code(self, code: str) -> str:
        return self.sandbox_service.run_code(code)

    def adjust_think_interval(self, duration: int) -> str:
        new_interval = max(self.think_interval_min, min(duration * 60, self.think_interval_max))
        self.current_think_interval = new_interval
        return f"Think interval adjusted to {new_interval // 60} minutes."

    async def handle_oracle_message(self, message: str, msg_type: str, message_id: Optional[int] = None) -> str:
        if not self.oracle_service:
            raise RuntimeError("Oracle service not initialized")
        return await self.oracle_service.handle_message(message, msg_type, message_id)

    async def control_led(self, state: str) -> str:
        led_path = "/sys/class/leds/nanopi-k2:blue:stat"
        if not os.path.exists(led_path):
            return "❌ LED control not available on this system."

        state = state.lower()
        if state not in ["on", "off", "heartbeat", "default-on", "none"]:
            return "❌ Invalid state. Use: on, off, heartbeat."

        try:
            trigger_file = f"{led_path}/trigger"
            brightness_file = f"{led_path}/brightness"

            if state == "on":
                with open(trigger_file, "w") as f:
                    f.write("none")
                with open(brightness_file, "w") as f:
                    f.write("1")
                msg = "LED turned ON"
            elif state == "off":
                with open(trigger_file, "w") as f:
                    f.write("none")
                with open(brightness_file, "w") as f:
                    f.write("0")
                msg = "LED turned OFF"
            elif state == "heartbeat":
                with open(trigger_file, "w") as f:
                    f.write("heartbeat")
                msg = "LED set to HEARTBEAT mode"
            else:
                with open(trigger_file, "w") as f:
                    f.write(state)
                msg = f"LED trigger set to {state}"

            await self.report_activity("led_control", msg)
            return f"✅ {msg}"
        except Exception as e:
            logger.error(f"[BRAIN] ❌ LED control failed: {e}")
            return f"❌ Failed to control LED: {e}"
