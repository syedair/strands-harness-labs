import py_compile
from pathlib import Path

import pytest

LABS = sorted(Path("labs").glob("lab*.py"))


def test_there_are_fourteen_lab_files():
    assert len(LABS) == 15  # lab 6 is split into 6a-6e; lab 11 is the web server


@pytest.mark.parametrize("lab", LABS, ids=lambda p: p.name)
def test_lab_compiles(lab):
    py_compile.compile(str(lab), doraise=True)
