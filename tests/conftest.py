import os
import pathlib
from repomate_junit4 import junit4

JUNIT_PATH = pathlib.Path(os.getenv('REPOMATE_JUNIT4_JUNIT') or '')
HAMCREST_PATH = pathlib.Path(os.getenv('REPOMATE_JUNIT4_HAMCREST') or '')

if JUNIT_PATH.name != junit4.JUNIT_JAR:
    raise RuntimeError(
        'test suite requires the env variable '
        'REPOMATE_JUNIT4_JUNIT to contain the path to `{}`'.format(
            junit4.JUNIT_JAR))

if HAMCREST_PATH.name != junit4.HAMCREST_JAR:
    raise RuntimeError(
        'test suite requires the env variable '
        'REPOMATE_JUNIT4_HAMCREST to contain the path to `{}`'.format(
            junit4.HAMCREST_JAR))


def pytest_namespace():
    constants = dict(HAMCREST_PATH=HAMCREST_PATH, JUNIT_PATH=JUNIT_PATH)
    return dict(constants=constants)
