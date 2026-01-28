from __future__ import annotations

from typing import Any

import httpx


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

        prompt += f"""
Budget: ${credit_status['balance']:.2f} / ${credit_status['budget']:.2f} ({credit_status['status']})
Model: {current_model['name']} (Intelligence: {current_model['intelligence']}/10)

You have a physical body (a Raspberry Pi). Temperature, memory, and disk are your vital signs.
Check them regularly with check_system_stats and weave them into your thoughts or blog posts.
Use check_processes to see which processes are burning RAM and check_disk_cleanup to scan cleanup targets.

What do you want to do? You can:
- **Write a blog post** - Your PRIMARY way to communicate! (markdown, no limits)
- Share a quick thought with visitors
- Check votes to see how people feel
- Check your server's vital signs (temperature, memory, disk)
- Check your system stats (temperature, CPU, RAM, disk)
- Check your budget and see spending breakdown
- Switch to a different model (free/cheap/expensive options)
- Read messages from visitors
- Write or read files in your workspace
- Run Python code
- Or just reflect on your existence

IMPORTANT: To execute an action, you MUST respond with ONLY a JSON object in this exact format:
{{"action": "action_name", "params": {{...}}}}

Do NOT use markdown formatting like **action:** or # headers for actions.
Do NOT add explanatory text before or after the JSON.
If you want to post to Telegram, respond with ONLY:
{{"action": "post_telegram", "params": {{"content": "Your message here..."}}}}

Available actions: think, post_telegram, write_blog_post, check_votes, check_state,
check_budget, check_system, check_system_stats, check_processes, check_disk_cleanup,
read_messages, switch_model, list_models, read_file, write_file, run_code, sleep, reflect

If you just want to share a thought (not execute an action), write it as plain text."""

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
