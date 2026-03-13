from backend.app.domain.models import ActionType
from backend.app.infrastructure.gemini_computer_use_client import _map_function_call


def test_map_click_at_to_coordinate_click_action() -> None:
    actions = _map_function_call("click_at", {"x": 500, "y": 300})
    assert len(actions) == 1
    assert actions[0].action == ActionType.CLICK
    assert actions[0].target.type == "computer_use_coordinates"
    assert actions[0].target.x == 500
    assert actions[0].target.y == 300


def test_map_type_text_at_to_coordinate_type_action() -> None:
    actions = _map_function_call(
        "type_text_at", {"x": 100, "y": 200, "text": "hello", "press_enter": True}
    )
    assert len(actions) == 1
    assert actions[0].action == ActionType.TYPE
    assert actions[0].value == "hello"
    assert actions[0].press_enter is True


def test_unsupported_function_returns_no_actions() -> None:
    actions = _map_function_call("unsupported_fn", {})
    assert actions == []
