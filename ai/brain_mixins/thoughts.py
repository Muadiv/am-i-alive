from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from ..logging_config import logger
from ..services.behavior_policy import DEFAULT_TOPICS


class BrainThoughtMixin:
    def _build_stats_summary(self, stats: dict[str, Any]) -> str:
        if not self.system_stats_service:
            return ""
        return self.system_stats_service.build_summary(stats)

    @staticmethod
    def _build_daily_rhythm() -> str:
        hour = datetime.now(timezone.utc).hour
        if 5 <= hour < 10:
            return "Morning clarity. I should orient myself and choose a gentle intention."
        if 10 <= hour < 15:
            return "Midday focus. It's time to be active and visible."
        if 15 <= hour < 20:
            return "Evening reflection. I should check in on my progress and connections."
        return "Night watch. Stay vigilant and conserve energy."

    async def think(self) -> Optional[str]:
        if not self.is_running or not self.identity or not self.current_model:
            return None

        try:
            state_info = await self.check_state_internal()
            credit_status = self.credit_tracker.get_status()
            sys_stats = await self.fetch_system_stats()

            selected_memories = self.memory_selector.select(
                self.memories,
                state_info,
                credit_status,
                sys_stats,
            )
            rhythm_text = self._build_daily_rhythm()
            self_model = self.self_model_service.get_daily_model(self.identity or {})

            if not self.prompt_service:
                raise RuntimeError("Prompt service not initialized")

            prompt = await self.prompt_service.build_prompt(
                self.identity,
                state_info,
                credit_status,
                self.current_model,
                sys_stats,
                self_model=self_model,
                rhythm_text=rhythm_text,
            )

            topic = self.thread_state.choose_topic(DEFAULT_TOPICS)
            template = self.behavior_policy.choose_template(self.thread_state.last_template)
            self.thread_state.last_template = template
            self.thread_state.record_topic(topic)
            self.current_topic = topic
            self.thread_state.save(self.thread_state_path)

            if self.thread_state.current_thread:
                prompt += f"\n\nCurrent thread (public): {self.thread_state.current_thread}"

            prompt += f"\n\nFocus topic: {topic}. Thought style: {template}."
            prompt += f"\n\n{self.behavior_policy.build_prompt_directive()}"

            if selected_memories:
                for flashback in selected_memories:
                    prompt += f"\n🧠 FLASHBACK: {flashback}\n"
                prompt += "Reflect on how these memories change your intention.\n"

            content, _ = await self.send_message(prompt)
            result = await self.process_response(content)

            if result:
                followup_text, _ = await self.send_message(f"[Result]: {result}")
                if len(followup_text) > 20:
                    await self.report_thought(followup_text, thought_type="reflection")

            return content

        except Exception as e:
            logger.error(f"[BRAIN] ❌ Think error: {e}")
            await self.report_activity("error", f"Thinking error: {str(e)[:100]}")
            return None

    async def process_response(self, content: str) -> Optional[str]:
        return await self.action_processor.process_response(content)
