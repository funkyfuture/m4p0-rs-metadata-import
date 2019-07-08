from pathlib import Path
from types import SimpleNamespace

from pytest import fixture


@fixture()
def test_config():
    yield SimpleNamespace()


@fixture(scope="session")
def test_data():
    yield Path(__file__).parent / "data"
