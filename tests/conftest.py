import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mlg.memory import Memory  # noqa: E402


@pytest.fixture
def memory(tmp_path):
    m = Memory(tmp_path / "test.db")
    yield m
    m.close()


def run(coro):
    return asyncio.run(coro)
