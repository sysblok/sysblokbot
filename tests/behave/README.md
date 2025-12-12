# Behave Tests for Telegram Bot

This directory contains behave-style BDD tests for the Telegram bot.

## Running Tests

From the project root, activate the virtual environment and run:

```bash
source env/bin/activate
behave tests/behave/features/
```

Or run a specific feature:

```bash
behave tests/behave/features/shrug_command.feature
```

## Test Structure

- `features/` - Gherkin feature files defining test scenarios
- `steps/` - Step definitions implementing the test steps
- `fixtures.py` - Test utilities and mock objects
- `environment.py` - Behave environment setup/teardown

## How It Works

The tests use a fully mocked environment:
- All Telegram interactions are mocked (no real API calls)
- Database is in-memory SQLite (recreated for each scenario)
- Bot handlers are tested directly without polling
- Messages are captured instead of being sent

This makes tests:
- Fast (no network calls)
- Deterministic (no external dependencies)
- CI-friendly (can run in docker compose networks)

