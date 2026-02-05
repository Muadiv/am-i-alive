from ai.services.behavior_policy import DEFAULT_TOPICS
from ai.services.thread_state import ThreadState


def test_choose_topic_avoids_recent():
    state = ThreadState()
    state.record_topic(DEFAULT_TOPICS[0])
    topic = state.choose_topic(DEFAULT_TOPICS)
    assert topic != DEFAULT_TOPICS[0]


def test_set_thread_builds_public_summary():
    state = ThreadState()
    state.set_thread("Test Title", "First sentence. Second sentence.", "survival strategy")
    assert "Current thread" in state.current_thread
    assert "Test Title" in state.current_thread
