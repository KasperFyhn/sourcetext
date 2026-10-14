import pytest


@pytest.fixture(autouse=True)
def _isolated_working_directory(tmp_path, monkeypatch):
    # SourceText picks up a default notes file from the working directory; keep
    # tests independent of whatever is in the directory pytest is run from.
    monkeypatch.chdir(tmp_path)
