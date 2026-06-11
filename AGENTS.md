# AGENTS.md — prozorro-catalog

Python aiohttp async REST API for the Prozorro procurement catalog. Backend uses MongoDB (Motor). Models are Pydantic v2.

## Project layout

```
src/
  catalog/           # main application package
    handlers/        # HTTP request handlers (PydanticView)
    models/          # Pydantic data models (input/output shapes)
    serializers/     # output serializers (whitelist fields, nest sub-serializers)
    state/           # business logic (lifecycle hooks: on_post, on_patch)
    migrations/      # one-off DB migration scripts
    analyzers/       # diagnostic/analytics scripts (read-only)
    api.py           # app factory + route registration
    db.py            # MongoDB access layer (all DB calls go here)
    auth.py          # authentication / accreditation
    middleware.py    # aiohttp middlewares
    settings.py      # env-based config
    utils.py         # shared helpers
    validations.py   # shared validation helpers

  cron/              # scheduled background tasks
  seed/              # DB seed scripts for dev/test

tests/
  integration/       # integration tests for handlers (use live test DB)
  tasks/             # tests for cron jobs and crawler
  migrations/        # tests for migration scripts
  fixtures/          # JSON fixtures (one per entity)
  conftest.py        # pytest fixtures (api client, db, entity factories)
  base.py            # shared test constants (TEST_AUTH, etc.)
  utils.py           # test helpers (create_criteria, create_profile, get_fixture_json)

docs/                # feature documentation (Markdown + PlantUML)
helm/                # Kubernetes Helm chart
```

## Where to create files

### New API resource (e.g. `widget`)

| What | Where | Example |
|------|-------|---------|
| Data model | `src/catalog/models/widget.py` | `src/catalog/models/vendor.py` |
| Serializer | `src/catalog/serializers/widget.py` | `src/catalog/serializers/vendor.py` |
| State / business logic | `src/catalog/state/widget.py` | `src/catalog/state/vendor.py` |
| Handler (views) | `src/catalog/handlers/widget.py` | `src/catalog/handlers/vendor.py` |
| Register routes | `src/catalog/api.py` — `create_application()` | — |
| JSON fixture | `tests/fixtures/widget.json` | `tests/fixtures/vendor.json` |
| Integration tests | `tests/integration/test_widget.py` | `tests/integration/test_vendor.py` |

For crowd-sourcing sub-resources place handler under `src/catalog/handlers/crowd_sourcing/`.

### New DB migration

File: `src/catalog/migrations/cs_NNNNN_short_description.py`

Where `NNNNN` is the Jira/CS ticket number. Each migration exposes a `migrate()` async coroutine and a `main()` entry point. Use `src/catalog/migrations/utils.py` for bulk-update helpers.

Example: `src/catalog/migrations/cs_21351_set_localization_tag.py`

### New cron task

File: `src/cron/my_task.py` + entry in `src/cron/cron.txt`

Test: `tests/tasks/test_my_task.py`

### New analyzer (read-only diagnostic)

File: `src/catalog/analyzers/cs_NNNNN_description.py`

### Documentation for a feature

Directory: `docs/<feature_name>/README.md` (add PlantUML diagrams if relevant).

## Architecture conventions

**Handler → State → DB flow**

1. Handler (`PydanticView`) validates HTTP input via Pydantic, then calls `State.on_post` / `State.on_patch`.
2. State mutates the data dict (sets `id`, `dateCreated`, `dateModified`, `status`, runs business-rule validations).
3. Handler calls `db.*` directly for persistence.
4. Handler uses `Serializer` to build the response dict.

**Models** define input/output shapes only — no business logic.
`Input[T]` / `AuthorizedInput[T]` wrap POST body. `Response[T]` / `CreateResponse[T]` wrap GET/POST responses.

**Serializers** (`RootSerializer`) control which fields are exposed and how nested objects are serialized. Define a `whitelist` set to restrict fields or add sub-serializers via the `serializers` dict.

**State** classes are plain classes (no instances) — all methods are `@classmethod` or `@staticmethod`. Inherit from `BaseState`.

**`src/catalog/validations.py` — do not use.** It is considered unnecessary abstraction: all validations and business rules belong in the relevant `State` class methods (`on_post`, `on_patch`, or a dedicated `@classmethod`).

**DB layer** (`src/catalog/db.py`) is the only place that touches MongoDB. All collections and CRUD helpers live there.

## Testing

- Tests use `pytest-aiohttp` with a real (flushed) MongoDB instance.
- The `api` fixture provides an async test client; `db` fixture inits and flushes the DB.
- Load fixture data with `api.get_fixture_json("entity_name")` (reads from `tests/fixtures/`).
- Auth: import `TEST_AUTH` / `TEST_AUTH_CPB` / `TEST_AUTH_NO_PERMISSION` from `tests/base`.
- Run tests: `pytest tests/` (requires MongoDB running, see `docker-compose.yml`).

## Code style

- Line length: 120 characters (Black).
- Formatter: Black + isort. Linter: ruff, pylint, bandit.
- Python ≥ 3.13 required.
- Strings: use single quotes (Black `skip-string-normalization = true`).
