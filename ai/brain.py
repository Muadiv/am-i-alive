"""Am I Alive? - Brain entrypoint wrapper."""

from __future__ import annotations

from .brain_core import AIBrain
from .brain_runtime import (
    brain_loop,
    birth_event,
    is_running,
    main_loop,
    pending_birth_data,
    queue_birth_data,
    run_main,
)
from .brain_shared import INTERNAL_API_KEY

__all__ = [
    "AIBrain",
    "INTERNAL_API_KEY",
    "brain_loop",
    "birth_event",
    "is_running",
    "main_loop",
    "pending_birth_data",
    "queue_birth_data",
    "run_main",
]


if __name__ == "__main__":
    run_main()
