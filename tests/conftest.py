from pathlib import Path
from types import SimpleNamespace

from pytest import fixture


@fixture()
def test_config():
    yield SimpleNamespace(
        entities_namespace="https://enter.museum4punkt0.de/resource/",
        media_types={
            "tif": "https://www.iana.org/assignments/media-types/image/tiff",
            "tiff": "https://www.iana.org/assignments/media-types/image/tiff",
        },
    )


@fixture(scope="session")
def test_data():
    yield Path(__file__).parent / "data"
