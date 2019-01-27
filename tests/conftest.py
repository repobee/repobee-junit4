from repomate_junit4 import junit4

from envvars import JUNIT_PATH, HAMCREST_PATH

if JUNIT_PATH.name != junit4.JUNIT_JAR:
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOMATE_JUNIT4_JUNIT to contain the path to `{}`".format(junit4.JUNIT_JAR)
    )

if HAMCREST_PATH.name != junit4.HAMCREST_JAR:
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOMATE_JUNIT4_HAMCREST to contain the path to `{}`".format(
            junit4.HAMCREST_JAR
        )
    )
