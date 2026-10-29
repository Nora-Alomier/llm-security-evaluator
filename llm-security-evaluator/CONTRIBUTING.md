# Contributing

Thank you for improving LLM Security Evaluator. Keep contributions local-first, safe, focused,
and easy to review.

## Development setup

1. Fork and clone the repository.
2. Create a Python 3.12 virtual environment.
3. Run `python -m pip install -e ".[dev]"`.
4. Create a branch from `main`.

Before submitting a pull request, run:

```bash
ruff check .
pytest
```

Add tests for behavior changes and update documentation for user-visible changes. Test cases must
use synthetic information and safe, non-operational prompts. Do not add real credentials,
dangerous procedural content, paid services, telemetry, or network dependencies to unit tests.

Use clear commit messages and explain the problem, approach, test evidence, and security/privacy
impact in the pull request. By contributing, you agree that your work is licensed under MIT.

