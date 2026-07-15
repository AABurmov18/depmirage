"""Typosquat / lookalike detection against a bundled popular-package list.

Pure Python Levenshtein (no C extensions) so it builds clean on Windows.
"""

from __future__ import annotations

from typing import List, Optional

from .parsers import pypi_normalize

# ~200 of the most-installed PyPI packages, bundled so we make ZERO network
# calls for this check. Names are stored PEP 503-normalized (lower, dashes).
POPULAR_PACKAGES: List[str] = [
    "boto3", "botocore", "urllib3", "requests", "setuptools", "certifi",
    "idna", "charset-normalizer", "python-dateutil", "typing-extensions",
    "six", "s3transfer", "pyyaml", "packaging", "numpy", "wheel", "pip",
    "cryptography", "awscli", "jmespath", "attrs", "click", "rsa",
    "pyasn1", "cffi", "pycparser", "markupsafe", "jinja2", "colorama",
    "google-api-core", "protobuf", "importlib-metadata", "zipp", "wrapt",
    "pytz", "pandas", "pydantic", "pydantic-core", "annotated-types",
    "aiohttp", "aiosignal", "frozenlist", "multidict", "yarl", "async-timeout",
    "flask", "werkzeug", "itsdangerous", "grpcio", "google-auth",
    "cachetools", "pyasn1-modules", "oauthlib", "requests-oauthlib",
    "websocket-client", "sqlalchemy", "greenlet", "pyparsing", "docutils",
    "chardet", "filelock", "platformdirs", "distlib", "virtualenv", "tomli",
    "more-itertools", "jsonschema", "pygments", "psutil", "scipy",
    "matplotlib", "kiwisolver", "cycler", "fonttools", "pillow", "pyarrow",
    "fsspec", "tqdm", "regex", "joblib", "scikit-learn", "threadpoolctl",
    "networkx", "sympy", "mpmath", "torch", "tensorflow", "keras",
    "transformers", "tokenizers", "huggingface-hub", "safetensors",
    "openai", "anthropic", "tiktoken", "langchain", "langchain-core",
    "langsmith", "google-cloud-storage", "google-cloud-core",
    "google-resumable-media", "google-crc32c", "grpcio-status",
    "googleapis-common-protos", "proto-plus", "redis", "celery", "kombu",
    "amqp", "billiard", "vine", "pymongo", "psycopg2", "psycopg2-binary",
    "mysqlclient", "pymysql", "asyncpg", "alembic", "mako", "django",
    "djangorestframework", "asgiref", "sqlparse", "gunicorn", "uvicorn",
    "starlette", "fastapi", "httpx", "httpcore", "h11", "anyio", "sniffio",
    "python-multipart", "email-validator", "dnspython", "orjson", "ujson",
    "msgpack", "lxml", "beautifulsoup4", "soupsieve", "html5lib", "cssselect",
    "scrapy", "twisted", "pyopenssl", "pynacl", "bcrypt", "paramiko",
    "pexpect", "ptyprocess", "future", "toml", "tomlkit", "pytest",
    "pluggy", "iniconfig", "coverage", "mock", "freezegun", "faker",
    "factory-boy", "hypothesis", "nose", "tox", "flake8", "pycodestyle",
    "pyflakes", "mccabe", "black", "isort", "mypy", "mypy-extensions",
    "pylint", "astroid", "bandit", "pre-commit", "cfgv", "identify",
    "nodeenv", "sentry-sdk", "prometheus-client", "gitpython", "gitdb",
    "smmap", "rich", "shellingham", "typer", "markdown", "markdown-it-py",
    "mdurl", "docker", "kubernetes", "pyjwt", "cryptg", "passlib",
    "argon2-cffi", "argon2-cffi-bindings", "python-dotenv", "environs",
    "marshmallow", "webencodings", "tenacity", "backoff", "cloudpickle",
    "dill", "pyzmq", "tornado", "notebook", "jupyter-core", "jupyter-client",
    "ipython", "ipykernel", "traitlets", "nbconvert", "nbformat",
    "prompt-toolkit", "wcwidth", "decorator", "pickleshare", "babel",
    "gspread", "pytest-cov", "pytest-mock", "pytest-asyncio", "watchdog",
    "opentelemetry-api", "grpc-google-iam-v1", "pycparser", "termcolor",
    "absl-py", "gast", "opt-einsum", "flatbuffers", "wandb", "datasets",
]

# De-dup while preserving order (in case of accidental repeats above).
_seen = set()
_POPULAR = []
for _p in POPULAR_PACKAGES:
    _n = pypi_normalize(_p)
    if _n not in _seen:
        _seen.add(_n)
        _POPULAR.append(_n)
POPULAR_SET = set(_POPULAR)


def levenshtein(a: str, b: str) -> int:
    """Classic dynamic-programming edit distance (insert/delete/substitute).

    Pure Python, O(len(a) * len(b)) time, O(min) space. No dependencies.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Keep the shorter string as the inner loop for less memory.
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            substitute = previous[j - 1] + (ca != cb)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


def nearest_popular(name: str, max_distance: int = 1) -> Optional[str]:
    """Return a popular package within ``max_distance`` edits, or None.

    An exact match returns None — it is the real package, not a lookalike.
    """
    norm = pypi_normalize(name)
    if norm in POPULAR_SET:
        return None
    best = None
    best_dist = max_distance + 1
    for pop in _POPULAR:
        # Cheap length pre-filter: distance >= |len difference|.
        if abs(len(pop) - len(norm)) > max_distance:
            continue
        d = levenshtein(norm, pop)
        if d < best_dist:
            best_dist = d
            best = pop
            if d == 1:  # can't get closer than 1 for a non-equal name
                break
    if best is not None and best_dist <= max_distance:
        return best
    return None
