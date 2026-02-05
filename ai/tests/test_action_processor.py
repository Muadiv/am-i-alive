import pytest

from ai.core.action_processor import ActionProcessor


class DummyExecutor:
    async def execute_action(self, action, params):
        return "ok"


@pytest.mark.asyncio
async def test_extracts_last_json_action():
    processor = ActionProcessor(DummyExecutor(), lambda *_args, **_kwargs: ("", {}), lambda *_args, **_kwargs: None)
    content = (
        "Thought first. {\"action\":\"check_votes\",\"params\":{}} "
        "Then another. {\"action\":\"write_blog_post\",\"params\":{\"title\":\"T\",\"content\":\"Body" 
        " with enough length to pass the threshold.\"}}"
    )
    data = processor.extract_action_data(content)
    assert data is not None
    assert data.get("action") == "write_blog_post"


def test_repairs_missing_brace():
    processor = ActionProcessor(DummyExecutor(), lambda *_args, **_kwargs: ("", {}), lambda *_args, **_kwargs: None)
    content = "Thought. {\"action\":\"check_votes\",\"params\":{}"
    data = processor.extract_action_data(content)
    assert data is not None
    assert data.get("action") == "check_votes"
