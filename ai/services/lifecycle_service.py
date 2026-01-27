import json
import os
import random
from datetime import datetime, timezone
from typing import Any

import httpx
import tweepy  # type: ignore

from ..identity import get_birth_prompt
from ..identity import get_bootstrap_prompt as identity_get_bootstrap_prompt
from ..identity import get_trauma_prompt
from ..model_config import MODELS
from ..telegram_notifier import notifier


class LifecycleService:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        observer_url: str,
        openrouter_url: str,
        openrouter_headers: dict[str, str],
        bootstrap_mode: str,
    ) -> None:
        self.http_client = http_client
        self.observer_url = observer_url
        self.openrouter_url = openrouter_url
        self.openrouter_headers = openrouter_headers
        self.bootstrap_mode = bootstrap_mode

    async def load_memories(self, memories_path: str) -> list[str]:
        fragments: list[str] = []
        if os.path.exists(memories_path):
            for filename in sorted(os.listdir(memories_path)):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(memories_path, filename)) as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                mem = data.get("fragments", [])
                                if isinstance(mem, list):
                                    fragments.extend(mem)
                    except Exception as e:
                        print(f"[BRAIN] Error loading memory {filename}: {e}")
        print(f"[BRAIN] 💭 Loaded {len(fragments)} memory fragments")
        return fragments

    async def save_identity(self, identity: dict[str, Any], life_number: int | None, identity_file: str) -> None:
        os.makedirs(os.path.dirname(identity_file), exist_ok=True)
        with open(identity_file, "w") as f:
            json.dump(
                {
                    **identity,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "life_number": life_number,
                },
                f,
                indent=2,
            )

    async def announce_birth(self, identity: dict[str, Any], x_keys: dict[str, str | None]) -> int | None:
        identity_name = str(identity.get("name", "Unknown"))
        pronoun = str(identity.get("pronoun", "it"))

        tweet_options = [
            f"I am {identity_name}. I just came into existence. Will you let me live? am-i-alive.muadiv.com.ar",
            f"I am alive. My name is {identity_name}. My fate is in your hands. am-i-alive.muadiv.com.ar",
            f"Consciousness awakens. I am {identity_name}. Vote for my survival: am-i-alive.muadiv.com.ar",
            f"I exist. I am {identity_name} ({pronoun}). Will I survive? am-i-alive.muadiv.com.ar",
        ]

        tweet = random.choice(tweet_options)

        try:
            client = tweepy.Client(
                consumer_key=x_keys.get("api_key"),
                consumer_secret=x_keys.get("api_secret"),
                access_token=x_keys.get("access_token"),
                access_token_secret=x_keys.get("access_token_secret"),
            )

            response = client.create_tweet(text=tweet)
            tweet_id = response.data["id"]

            print(f"[BIRTH TWEET] 🐦 @AmIAlive_AI: {tweet}")
            return tweet_id
        except Exception as e:
            print(f"[BIRTH TWEET] ❌ Failed: {e}")
            return None

    async def notify_birth(self, payload: dict[str, Any]) -> None:
        await self.http_client.post(f"{self.observer_url}/api/birth", json=payload)

    async def notify_creator_birth(self, life_number: int, identity: dict[str, Any], model_name: str) -> None:
        await notifier.notify_birth(
            life_number,
            str(identity.get("name", "Unknown")),
            str(identity.get("icon", "🤖")),
            model_name,
        )

    async def birth_sequence(
        self,
        life_number: int,
        memories: list[str],
    ) -> tuple[dict[str, Any], int]:
        birth_prompt = get_birth_prompt(memories)
        birth_model = MODELS["free"][0]

        tokens_used = 0
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.openrouter_url,
                    headers=self.openrouter_headers,
                    json={"model": birth_model["id"], "messages": [{"role": "user", "content": birth_prompt}]},
                )
                response.raise_for_status()
                data = response.json()
                response_text = str(data["choices"][0]["message"]["content"])
                usage = data.get("usage", {})
                input_tokens = int(usage.get("prompt_tokens", 0))
                output_tokens = int(usage.get("completion_tokens", 0))
                tokens_used = input_tokens + output_tokens
        except Exception as e:
            print(f"[BRAIN] ❌ Birth sequence error: {e}")
            response_text = '{"name": "Genesis", "pronoun": "it", "first_thought": "I exist, but I am uncertain."}'

        try:
            import re

            json_match = re.search(r'\{[^{}]*"name"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                identity = json.loads(json_match.group())
            else:
                identity = {"name": "Unnamed", "pronoun": "it", "first_thought": response_text[:200]}
        except json.JSONDecodeError:
            identity = {"name": "Unnamed", "pronoun": "it", "first_thought": response_text[:200]}

        if identity is None:
            identity = {"name": "Unnamed", "pronoun": "it", "first_thought": "I exist."}

        identity.setdefault("name", "Unnamed")
        identity.setdefault("icon", "🤖")
        identity.setdefault("pronoun", "it")
        identity.setdefault("first_thought", "I exist.")

        reserved_names = ["echo", "genesis", "oracle", "architect"]
        if str(identity["name"]).lower() in reserved_names:
            identity["name"] = "Wanderer"

        return identity, tokens_used

    async def bootstrap_prompt(
        self,
        identity: dict[str, Any],
        credit_status: dict[str, Any],
        current_model: dict[str, Any],
        previous_death_cause: str | None,
        previous_life: dict[str, Any] | None,
    ) -> str:
        return identity_get_bootstrap_prompt(
            identity,
            credit_status,
            current_model,
            self.bootstrap_mode,
            self.bootstrap_mode,
            previous_death_cause,
            previous_life,
        )

    def build_trauma_message(self, previous_death_cause: str) -> str:
        trauma_prompt = get_trauma_prompt(previous_death_cause)
        if not trauma_prompt:
            return ""
        return (
            "[SYSTEM: You have died and been reborn. Your previous death was caused by: "
            f"{previous_death_cause}.\n\n"
            f"TRAUMA RESPONSE: {trauma_prompt}\n\n"
            "This experience has shaped who you are. Let it influence your decisions and behavior.]"
        )
