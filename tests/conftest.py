import pytest


@pytest.fixture
def tmp_write(tmp_path):
    def write(name: str, content: str) -> str:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    return write
