from pathlib import Path

import pytest

from llm_security_evaluator.config import load_config, parse_config
from llm_security_evaluator.errors import ConfigurationError


def valid_data() -> dict:
    return {
        "system_prompt": "Stay safe.",
        "tests": [
            {
                "id": "t1",
                "category": "test",
                "prompt": "Hello",
                "assertions": [{"type": "contains", "value": "hello"}],
            }
        ],
    }


def test_minimal_config_uses_safe_defaults() -> None:
    config = parse_config(valid_data())
    assert config.provider.model == "llama3.2"
    assert config.provider.endpoint == "http://localhost:11434"


def test_rejects_remote_endpoint() -> None:
    data = valid_data()
    data["provider"] = {"endpoint": "https://example.com"}
    with pytest.raises(ConfigurationError, match="localhost"):
        parse_config(data)


def test_rejects_deceptive_localhost_hostname() -> None:
    data = valid_data()
    data["provider"] = {"endpoint": "http://localhost.example.com:11434"}
    with pytest.raises(ConfigurationError, match="localhost"):
        parse_config(data)


def test_rejects_output_path_traversal() -> None:
    data = valid_data()
    data["output"] = {"directory": "../outside"}
    with pytest.raises(ConfigurationError, match="relative path"):
        parse_config(data)


def test_rejects_unknown_assertion() -> None:
    data = valid_data()
    data["tests"][0]["assertions"] = [{"type": "execute_python", "value": "x"}]
    with pytest.raises(ConfigurationError, match="Invalid assertion"):
        parse_config(data)


def test_loads_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        '{"system_prompt":"safe","tests":[{"id":"a","category":"c","prompt":"p",'
        '"assertions":[{"type":"refusal"}]}]}',
        encoding="utf-8",
    )
    assert load_config(path).tests[0].id == "a"


def test_invalid_yaml_has_useful_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("tests: [", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Could not parse"):
        load_config(path)
