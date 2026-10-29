import os

import pytest

from llm_security_evaluator.models import GenerationConfig, ProviderConfig
from llm_security_evaluator.providers import OllamaProvider


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("LLMSEC_INTEGRATION") != "1", reason="set LLMSEC_INTEGRATION=1")
def test_real_local_ollama() -> None:
    with OllamaProvider(ProviderConfig()) as provider:
        response = provider.generate(
            "Reply only with OK", "Follow the user request.", GenerationConfig()
        )
    assert response.text.strip()
