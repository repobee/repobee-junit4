"""Environment variables that are needed for the tests."""

import pathlib
import os

JUNIT_PATH = pathlib.Path(os.getenv("REPOMATE_JUNIT4_JUNIT") or "")
HAMCREST_PATH = pathlib.Path(os.getenv("REPOMATE_JUNIT4_HAMCREST") or "")
