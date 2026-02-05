# TASK-004: System check tests
import os

import pytest


if not os.getenv("OPENROUTER_API_KEY"):
    pytest.skip("OPENROUTER_API_KEY not set for system checks", allow_module_level=True)


ai_brain = pytest.importorskip("ai.brain", reason="AI module not available in observer environment")
psutil = pytest.importorskip("psutil", reason="psutil not available in observer environment")


@pytest.mark.asyncio
async def test_check_system_returns_stats():
    """check_system should return host stats."""
    brain = ai_brain.AIBrain()
    brain.life_number = 1
    brain.credit_tracker.data = {"lives": {"1": {"start_time": "2026-01-09T12:00:00"}}}

    result = await brain.check_system()

    assert "SYSTEM" in result
    assert "HOST" in result
    assert "Memory" in result or "memory" in result.lower()


@pytest.mark.asyncio
async def test_system_stats_include_key_metrics():
    """System check should include CPU, memory, disk info."""
    brain = ai_brain.AIBrain()
    brain.life_number = 1
    brain.credit_tracker.data = {"lives": {"1": {"start_time": "2026-01-09T12:00:00"}}}

    result = await brain.check_system()

    assert "CPU" in result or "cpu" in result.lower()
    assert "Memory" in result or "memory" in result.lower() or "RAM" in result
    assert "Disk" in result or "disk" in result.lower()
