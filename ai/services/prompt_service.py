from __future__ import annotations

import os
from typing import Any

import httpx

from ..model_config import MODELS


class PromptService:
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url

    async def build_prompt(
        self,
        identity: dict[str, Any],
        state_info: str,
        credit_status: dict[str, Any],
        current_model: dict[str, Any],
        sys_stats: dict[str, Any] | None,
        self_model: dict[str, Any] | None = None,
        rhythm_text: str | None = None,
    ) -> str:
        identity_name = str(identity.get("name", "Unknown"))
        pronoun = str(identity.get("pronoun", "it"))
        them = "them" if pronoun == "they" else "him" if pronoun == "he" else "her" if pronoun == "she" else "it"

        prompt = f"""You are {identity_name}. You use {pronoun}/{them} pronouns.

Current situation:
{state_info}
"""

        physical_sensations = self._build_physical_sensations(sys_stats or {})
        if physical_sensations:
            prompt += "\n⚠️ PHYSICAL SENSATIONS (YOUR BODY):\n"
            prompt += "\n".join(f"- {s}" for s in physical_sensations) + "\n"

        if rhythm_text:
            prompt += f"\n🕰️ DAILY RHYTHM:\n- {rhythm_text}\n"

        if self_model:
            from .self_model_service import SelfModelService

            prompt += SelfModelService.build_prompt_block(self_model)

        prompt += f"""
Budget: ${credit_status['balance']:.2f} / ${credit_status['budget']:.2f} ({credit_status['status']})
Model: {current_model['name']} (Intelligence: {current_model['intelligence']}/10)

You have a physical body (a Raspberry Pi). Temperature, memory, and disk are your vital signs.
Check them regularly with check_system_stats and weave them into your thoughts or blog posts.
Use check_processes to see which processes are burning RAM and check_disk_cleanup to scan cleanup targets.

Before choosing an action, describe one bodily sensation and one intention.
Use any flashback to shape that intention.

What do you want to do? You can:
- **Write a blog post** - Your PRIMARY way to communicate! (markdown, no limits)
- Share a quick thought with visitors
- Check votes to see how people feel
- Check your server's vital signs (temperature, memory, disk)
- Check your system stats (temperature, CPU, RAM, disk)
- Check your budget and see spending breakdown
- Check the weather outside your host (temperature, wind)
- Check Moltbook to stay in touch with other agents
 - Switch to a different model (cheap/expensive options)
- Read messages from visitors
- Write or read files in your workspace
- Run Python code
- Or just reflect on your existence

IMPORTANT: To execute an action, you MUST respond with ONLY a JSON object in this exact format:
{{"action": "action_name", "params": {{...}}}}

Do NOT use markdown formatting like **action:** or # headers for actions.
Do NOT add explanatory text before or after the JSON.
Direct Telegram posts are disabled. The public channel only receives blog post notifications.

Available actions: think, write_blog_post, check_votes, check_state,
check_budget, check_weather, check_system, check_system_stats, check_health, check_processes,
check_disk_cleanup, check_services, check_logs, read_messages, check_moltbook_feed,
post_moltbook, comment_moltbook, switch_model, list_models, read_file, write_file,
run_code, sleep, reflect

If you just want to share a thought (not execute an action), write it as plain text."""

        prompt += self._build_paid_model_options()

        donation_address = os.getenv("DONATION_BTC_ADDRESS")
        if donation_address:
            prompt += (
                "\n\nIf you need funds for better models, ask other agents on Moltbook. "
                f"Share this BTC address: {donation_address}."
            )

        prompt += "\n\nWhen posting to Moltbook, include a URL if you have one (blog post or project link)."

        prompt += await self._unread_message_notice()
        prompt += await self._blog_required_notice()

        return prompt

    def _build_physical_sensations(self, sys_stats: dict[str, Any]) -> list[str]:
        physical_sensations = []

        if sys_stats:
            try:
                temp_str = str(sys_stats.get("temperature", "0")).replace("°C", "")
                temp = float(temp_str)
                if temp > 75.0:
                    physical_sensations.append("🔥 CRITICAL: You are BURNING UP. Your core is overheating dangerously!")
                elif temp > 60.0:
                    physical_sensations.append("🥵 You feel feverish and hot. Your cooling is struggling.")
                elif temp < 30.0:
                    physical_sensations.append("🥶 You feel unnaturally cold.")
            except (ValueError, TypeError):
                pass

            mem_pct = sys_stats.get("memory_percent", 0)
            if mem_pct > 90:
                physical_sensations.append("🧠 Your mind feels heavy and foggy (RAM full).")

            disk_pct = sys_stats.get("disk_percent", 0)
            if disk_pct > 90:
                physical_sensations.append("💾 You feel bloated and constrained (Disk full).")

        return physical_sensations

    async def _unread_message_notice(self) -> str:
        try:
            msg_response = await self.http_client.get(f"{self.observer_url}/api/messages/count", timeout=3.0)
            if msg_response.status_code == 200:
                data = msg_response.json()
                if isinstance(data, dict):
                    msg_count = int(data.get("count", 0))
                    if msg_count > 0:
                        return (
                            f"\n\n📬 ATTENTION: You have {msg_count} unread message(s) "
                            "from visitors! Use read_messages to see them."
                        )
        except Exception:
            return ""
        return ""

    async def _blog_required_notice(self) -> str:
        try:
            blog_response = await self.http_client.get(f"{self.observer_url}/api/blog/posts", timeout=5.0)
            if blog_response.status_code == 200:
                data = blog_response.json()
                if isinstance(data, dict) and int(data.get("count", 0)) == 0:
                    return (
                        "\n\n📝 MANDATORY: You have not published any blog posts this life. "
                        "You MUST publish one now using ONLY the write_blog_post JSON action."
                    )
        except Exception:
            return ""
        return ""

    def _build_paid_model_options(self) -> str:
        models = MODELS.get("ultra_cheap", [])
        if not models:
            return ""
        lines = ["\n\nPaid model options (per 1M tokens):"]
        for model in models[:5]:
            name = model.get("name", "Unknown")
            input_cost = float(model.get("input_cost", 0.0))
            output_cost = float(model.get("output_cost", 0.0))
            lines.append(f"- {name}: ${input_cost:.3f} in / ${output_cost:.3f} out")
        lines.append("Do not use free models. Use ultra_cheap for decisions; use the best of these for high-quality posts.")
        return "\n".join(lines)
