## Contributing

Thank you for considering a contribution! This guide explains how to get set up and submit changes.

### Prerequisites

- Python 3.12+
- Poetry

### Setup

  ```bash
  poetry install
  cp .env.example .env
  # Fill in openrouter_api_key in .env
  ```

### Running the app

  ```bash
  poetry run uvicorn server:app --reload
  ```

### Branches and Commits

- Use short, descriptive branches (e.g., `feat/add-docker`, `fix/transcript-error`).
- Follow Conventional Commits for messages:
  - `feat: add new user note editor`
  - `fix: handle transcripts without timestamps`
  - `docs: update README with setup steps`

### Tests

- Tests live under `test/`. If you change behavior, please update or add tests accordingly.

### Pull Requests

- Keep PRs small and focused.
- Describe the change and include screenshots if UI is affected.
- Link related issues.


