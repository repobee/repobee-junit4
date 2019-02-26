from repomate_junit4._junit4_runner import HAMCREST_JAR, JUNIT_JAR

from envvars import JUNIT_PATH, HAMCREST_PATH

if JUNIT_PATH.name != JUNIT_JAR:
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOMATE_JUNIT4_JUNIT to contain the path to `{}`".format(JUNIT_JAR)
    )

if HAMCREST_PATH.name != HAMCREST_JAR:
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOMATE_JUNIT4_HAMCREST to contain the path to `{}`".format(HAMCREST_JAR)
    )
