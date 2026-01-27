import json
import re
from typing import Any, Optional


class ActionProcessor:
    def __init__(self, action_executor, send_message, report_thought) -> None:
        self.action_executor = action_executor
        self.send_message = send_message
        self.report_thought = report_thought

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
                    print(f"[BRAIN] ✓ Extracted action: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass
            idx = text.find("{", idx + 1)

        fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                payload = json.loads(fenced.group(1))
                if isinstance(payload, dict) and payload.get("action"):
                    print(f"[BRAIN] ✓ Extracted action from fence: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass

        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and payload.get("action"):
                print(f"[BRAIN] ✓ Extracted action from full text: {payload.get('action')}")
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
            if action == "write_blog_post":
                title = params.get("title", "") if isinstance(params.get("title"), str) else ""
                body = params.get("content", "") if isinstance(params.get("content"), str) else ""
                if not title.strip() or len(body.strip()) < 100:
                    print("[BRAIN] ⚠️ write_blog_post missing title/content; requesting retry")
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
            print(f"[BRAIN] ⚠️  No action parsed from response: {preview}...")

        lowered = content.lower()
        if "blog" in lowered and ("write" in lowered or "post" in lowered):
            print("[BRAIN] ⚠️  Blog intent detected without action; requesting JSON action")
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
