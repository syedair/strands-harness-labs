import py_compile
from pathlib import Path

import pytest

LABS = sorted(Path("labs").glob("lab*.py"))


def test_there_are_ten_labs():
    assert len(LABS) == 10


@pytest.mark.parametrize("lab", LABS, ids=lambda p: p.name)
def test_lab_compiles(lab):
    py_compile.compile(str(lab), doraise=True)
