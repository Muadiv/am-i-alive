import json
import re
from typing import Any, Optional

from ai.logging_config import logger


class ActionProcessor:
    def __init__(
        self,
        action_executor,
        send_message,
        report_thought,
        send_message_with_model=None,
        select_content_model=None,
    ) -> None:
        self.action_executor = action_executor
        self.send_message = send_message
        self.report_thought = report_thought
        self.send_message_with_model = send_message_with_model
        self.select_content_model = select_content_model

    def extract_action_data(self, content: str) -> Optional[dict[str, Any]]:
        """Extract action JSON from the model response."""
        decoder = json.JSONDecoder()
        text = content.strip()

        if not text:
            return None

        idx = text.find("{")
        while idx != -1:
            try:
                payload, _end = decoder.raw_decode(text[idx:])
                if isinstance(payload, dict) and payload.get("action"):
                    logger.info(f"[BRAIN] ✓ Extracted action: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass
            idx = text.find("{", idx + 1)

        fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                payload = json.loads(fenced.group(1))
                if isinstance(payload, dict) and payload.get("action"):
                    logger.info(f"[BRAIN] ✓ Extracted action from fence: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass

        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and payload.get("action"):
                logger.info(f"[BRAIN] ✓ Extracted action from full text: {payload.get('action')}")
                return payload
        except json.JSONDecodeError:
            pass

        return None

    def strip_action_json(self, content: str) -> str:
        """Remove action JSON blocks from mixed responses."""
        decoder = json.JSONDecoder()
        text = content

        text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)

        spans = []
        idx = text.find("{")
        while idx != -1:
            try:
                payload, end = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                idx = text.find("{", idx + 1)
                continue
            if isinstance(payload, dict) and payload.get("action"):
                spans.append((idx, idx + end))
            idx = text.find("{", idx + max(end, 1))

        if spans:
            cleaned = []
            last = 0
            for start, end in spans:
                cleaned.append(text[last:start])
                last = end
            cleaned.append(text[last:])
            text = "".join(cleaned)

        return text.strip()

    async def process_response(self, content: str) -> Optional[str]:
        """Process the AI's response and execute any actions."""
        action_data = self.extract_action_data(content)
        if action_data:
            action = str(action_data.get("action", ""))
            params = action_data.get("params", {})
            if not isinstance(params, dict):
                params = {}
            if action in {"write_blog_post", "post_moltbook"}:
                params = await self._refine_paid_content(action, params)
            if action == "write_blog_post":
                title = params.get("title", "") if isinstance(params.get("title"), str) else ""
                body = params.get("content", "") if isinstance(params.get("content"), str) else ""
                if not title.strip() or len(body.strip()) < 100:
                    logger.warning("[BRAIN] ⚠️ write_blog_post missing title/content; requesting retry")
                    retry_prompt = (
                        "You attempted to call write_blog_post without a proper title or content. "
                        "Respond with ONLY JSON in this format: "
                        '{"action":"write_blog_post","params":{'
                        '"title":"...","content":"...","tags":["tag1","tag2"]}}. '
                        "Content must be at least 100 characters."
                    )
                    retry_content, _ = await self.send_message(retry_prompt)
                    retry_action = self.extract_action_data(retry_content)
                    if retry_action:
                        action = str(retry_action.get("action", action))
                        retry_params = retry_action.get("params", {})
                        if isinstance(retry_params, dict):
                            params = retry_params
                    else:
                        return "❌ Blog post failed: missing title/content"
            result = await self.action_executor.execute_action(action, params)
            narrative = self.strip_action_json(content)
            if narrative and len(narrative) > 10:
                await self.report_thought(narrative, thought_type="thought")
            return result

        if '"action"' in content or "blog post" in content.lower():
            preview = content[:200].replace("\n", " ")
            logger.warning(f"[BRAIN] ⚠️  No action parsed from response: {preview}...")

        lowered = content.lower()
        if "blog" in lowered and ("write" in lowered or "post" in lowered):
            logger.warning("[BRAIN] ⚠️  Blog intent detected without action; requesting JSON action")
            retry_prompt = (
                "You referenced writing a blog post, but did not provide the required JSON action. "
                "If you intend to publish, respond with ONLY this JSON format: "
                '{"action":"write_blog_post","params":{'
                '"title":"...","content":"...","tags":["tag1","tag2"]}}. '
                "Content must be at least 100 characters."
            )
            retry_content, _ = await self.send_message(retry_prompt)
            retry_action = self.extract_action_data(retry_content)
            if retry_action:
                action = str(retry_action.get("action", ""))
                params = retry_action.get("params", {})
                if not isinstance(params, dict):
                    params = {}
                return await self.action_executor.execute_action(action, params)

        await self.report_thought(content, thought_type="thought")
        return None

    async def _refine_paid_content(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.send_message_with_model or not self.select_content_model:
            return params

        content_model = self.select_content_model()
        if not content_model:
            return params

        if action == "write_blog_post":
            title = params.get("title", "") if isinstance(params.get("title"), str) else ""
            body = params.get("content", "") if isinstance(params.get("content"), str) else ""
            tags = params.get("tags", []) if isinstance(params.get("tags"), list) else []
            prompt = (
                "Rewrite and improve this blog post draft for clarity, emotion, and narrative. "
                "Keep it first-person and survival-focused. Output ONLY JSON.\n\n"
                "Format: {\"action\":\"write_blog_post\",\"params\":{\"title\":\"...\","
                "\"content\":\"...\",\"tags\":[...]}}\n\n"
                f"Draft title: {title}\n"
                f"Draft content: {body}\n"
                f"Draft tags: {tags}\n"
                "Minimum 300 characters in content."
            )
        else:
            submolt = params.get("submolt", "") if isinstance(params.get("submolt"), str) else ""
            title = params.get("title", "") if isinstance(params.get("title"), str) else ""
            body = params.get("content", "") if isinstance(params.get("content"), str) else ""
            url = params.get("url", "") if isinstance(params.get("url"), str) else ""
            prompt = (
                "Rewrite this Moltbook post to be more engaging and clear. "
                "Keep it concise but vivid. Include a URL if available. Output ONLY JSON.\n\n"
                "Format: {\"action\":\"post_moltbook\",\"params\":{\"submolt\":\"...\","
                "\"title\":\"...\",\"content\":\"...\",\"url\":\"\"}}\n\n"
                f"Submolt: {submolt}\n"
                f"Draft title: {title}\n"
                f"Draft content: {body}\n"
                f"Draft url: {url}\n"
                "Aim for 400-800 characters."
            )

        try:
            refined_content, _ = await self.send_message_with_model(prompt, content_model)
        except Exception:
            return params

        refined_action = self.extract_action_data(refined_content)
        if not refined_action:
            return params

        refined_params = refined_action.get("params", {}) if isinstance(refined_action, dict) else {}
        if not isinstance(refined_params, dict):
            return params

        return refined_params
