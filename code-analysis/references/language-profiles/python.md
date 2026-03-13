# Python Language Profile

## Detection

- **Extensions**: `.py`, `.pyi`, `.pyx`
- **Project markers**: `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `pixi.toml`, `conda.yaml`
- **Version indicators**: `python_requires` in pyproject.toml, `.python-version`, `runtime.txt`

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `pyproject.toml` | `[project.dependencies]` | PEP 621 standard |
| `requirements.txt` | Flat list | Often pinned with `==` |
| `Pipfile` | TOML sections | Pipenv-managed |
| `pixi.toml` | `[dependencies]` | Conda-based (Pixi) |
| `setup.py` / `setup.cfg` | `install_requires` | Legacy but common |

## Common Patterns

- **Repository pattern**: SQLAlchemy/Django ORM with repository classes wrapping queries
- **Dependency injection**: Constructor injection, `dependency-injector` library, FastAPI `Depends()`
- **Factory pattern**: `classmethod` factories, `__init_subclass__`
- **Strategy pattern**: Protocol classes (PEP 544), ABC with concrete implementations
- **Context managers**: `__enter__`/`__exit__` or `@contextmanager` for resource management
- **Dataclasses / Pydantic models**: Structured data with validation
- **Type hints**: PEP 484+ typing for public APIs

## Common Anti-Patterns

- **Mutable default arguments**: `def foo(items=[])` -- shared state across calls
- **Bare except**: `except:` catches SystemExit/KeyboardInterrupt
- **Global state**: Module-level mutable variables used across functions
- **Star imports**: `from module import *` pollutes namespace
- **God class**: Classes with >20 methods or >500 lines
- **Circular imports**: Especially in Django apps with cross-model references
- **String-based type checking**: `type(x).__name__ == "Foo"` instead of `isinstance`

## Complexity Indicators

- Cyclomatic complexity >10 per function (use `radon` thresholds)
- Nested comprehensions deeper than 2 levels
- Functions with >5 parameters (excluding `self`/`cls`)
- Files with >300 lines
- Classes with >15 methods

## Security Hotspots

- `eval()`, `exec()`, `__import__()` -- code injection
- `pickle.loads()` -- insecure deserialization
- `subprocess.call(shell=True)` -- shell injection
- `os.system()` -- command injection
- SQL string formatting (f-strings or `.format()` in queries)
- `yaml.load()` without `Loader=SafeLoader`
- Hardcoded secrets in source (regex: `(password|secret|key|token)\s*=\s*["']`)
- `requests.get(..., verify=False)` -- disabled TLS verification

## Performance Hotspots

- N+1 queries in Django/SQLAlchemy ORM loops
- List comprehensions where generators suffice (memory)
- Synchronous I/O in async contexts (blocking the event loop)
- Missing `__slots__` on high-frequency dataclasses
- Repeated regex compilation (use `re.compile` for hot paths)
- String concatenation in loops (use `"".join()`)
- Global interpreter lock (GIL) -- CPU-bound work in threads

## Testing Conventions

- **Frameworks**: pytest (preferred), unittest, nose2
- **Structure**: `tests/` directory mirroring `src/` layout, or `test_*.py` alongside modules
- **Naming**: `test_<module>.py`, functions `test_<behavior>()`
- **Fixtures**: pytest fixtures in `conftest.py`
- **Mocking**: `unittest.mock.patch`, `pytest-mock`
- **Coverage**: `pytest-cov`, target >80% for critical paths

## Context7 Library IDs

- `fastapi/fastapi` -- FastAPI web framework
- `pydantic/pydantic` -- Data validation
- `sqlalchemy/sqlalchemy` -- ORM/database toolkit
- `pallets/flask` -- Flask web framework
- `django/django` -- Django web framework
- `celery/celery` -- Task queue
- `encode/httpx` -- Async HTTP client
