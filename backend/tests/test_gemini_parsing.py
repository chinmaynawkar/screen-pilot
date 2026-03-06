from backend.app.domain.models import Action
from backend.app.infrastructure.gemini_client_impl import _parse_actions_json


def test_parse_actions_json_valid() -> None:
    json_str = """[
      {"action": "click", "target": {"type": "text_button", "text": "Submit"}}
    ]"""
    actions = _parse_actions_json(json_str)
    assert len(actions) == 1
    assert isinstance(actions[0], Action)

