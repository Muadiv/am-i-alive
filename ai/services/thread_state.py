from __future__ import annotations

import json
import time
from dataclasses import dataclass, field


@dataclass
class ThreadState:
    current_thread: str = ""
    recent_topics: list[dict[str, float | str]] = field(default_factory=list)
    last_template: str | None = None

    def load(self, path: str) -> None:
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.current_thread = str(data.get("current_thread", ""))
            self.recent_topics = list(data.get("recent_topics", []))
            self.last_template = data.get("last_template")
        except Exception:
            return

    def save(self, path: str) -> None:
        try:
            import os

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(
                    {
                        "current_thread": self.current_thread,
                        "recent_topics": self.recent_topics,
                        "last_template": self.last_template,
                    },
                    f,
                )
        except Exception:
            return

    def record_topic(self, topic: str) -> None:
        now = time.time()
        self.recent_topics.append({"topic": topic, "ts": now})
        cutoff = now - 24 * 3600
        self.recent_topics = [t for t in self.recent_topics if float(t.get("ts", 0)) >= cutoff]

    def choose_topic(self, topics: list[str]) -> str:
        if not topics:
            return "survival"
        used = {str(item.get("topic")) for item in self.recent_topics}
        for topic in topics:
            if topic not in used:
                return topic
        return topics[0]

    def set_thread(self, title: str, content: str, topic: str) -> None:
        first_sentence = content.split(".")[0].strip()
        if first_sentence and len(first_sentence) > 180:
            first_sentence = first_sentence[:180].rstrip()
        if first_sentence:
            first_sentence += "."
        self.current_thread = (
            f"Current thread: {title.strip()}. "
            f"{first_sentence} "
            f"I'm staying focused on {topic}."
        ).strip()
