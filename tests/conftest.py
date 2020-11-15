from repobee_junit4 import _junit4_runner
from envvars import JUNIT_PATH, HAMCREST_PATH
import re

if not re.search(_junit4_runner.JUNIT4_JAR_PATTERN, str(JUNIT_PATH)):
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOBEE_JUNIT4_JUNIT to contain the path to the junit4 jar"
    )

if not re.search(_junit4_runner.HAMCREST_JAR_PATTERN, str(HAMCREST_PATH)):
    raise RuntimeError(
        "test suite requires the env variable "
        "REPOBEE_JUNIT4_HAMCREST to contain the path to the hamcrest library"
    )
