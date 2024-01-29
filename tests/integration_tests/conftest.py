"""Fixtures for the integrations tests."""

import pytest
from pathlib import Path


def _remove_class_files(root=Path(__file__).parent):
    """Finds and removes every .class file in this directory, or any
    subdirectory.
    """
    class_files = list(root.rglob("*.class"))
    for file in class_files:
        file.unlink()


@pytest.fixture(scope="session", autouse=True)
def remove_class_files_session():
    """Remove class files before and after the test session starts."""
    _remove_class_files()
    yield
    _remove_class_files()


@pytest.fixture(autouse=True)
def remove_class_files_after_test_function():
    """Remove class files before each test executes."""
    _remove_class_files()
