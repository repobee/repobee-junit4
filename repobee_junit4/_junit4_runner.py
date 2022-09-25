import pathlib
import tempfile
import re
import sys
import subprocess
import os
import contextlib
from typing import Optional

import daiquiri

from repobee_junit4 import _java
from repobee_junit4 import _output


LOGGER = daiquiri.getLogger(__file__)
HAMCREST_JAR_PATTERN = rf"([^{os.pathsep}]*hamcrest-core-1.3.jar)"
JUNIT4_JAR_PATTERN = rf"([^{os.pathsep}]*junit-4\.\d+\.(\d+\.)?jar)"

_DEFAULT_SECURITY_POLICY_TEMPLATE = """grant {{
}};
grant codeBase "file:{junit4_jar_path}" {{
    permission java.lang.RuntimePermission "accessDeclaredMembers";
}};
"""


@contextlib.contextmanager
def security_policy(classpath: str, active: bool):
    """Yield the path to the default security policy file if ``active``,
    else yield None. The policy file is deleted once the context is
    exited.

    TODO: Make it possible to use a custom security policy here.
    """
    if not active:
        LOGGER.warning(
            "Security policy disabled, student code running without "
            "restrictions"
        )
        yield
        return

    with tempfile.NamedTemporaryFile() as security_policy_file:
        policy = _generate_default_security_policy(classpath)
        security_policy_file.write(
            policy.encode(encoding=sys.getdefaultencoding())
        )
        security_policy_file.flush()
        yield pathlib.Path(security_policy_file.name)


def _generate_default_security_policy(classpath: str) -> str:
    """Generate the default security policy from the classpath. JUnit4 jar must
    be on the classpath.
    """
    junit_jar_matches = re.search(JUNIT4_JAR_PATTERN, classpath)
    if not junit_jar_matches:
        raise ValueError("junit4 jar not on the classpath")
    path = junit_jar_matches.group(0)
    return _DEFAULT_SECURITY_POLICY_TEMPLATE.format(junit4_jar_path=path)


def _extract_conforming_package(test_class, prod_class):
    """Extract a package name from the test and production class.
    Raise if the test class and production class have different package
    statements.
    """
    test_package = _java.extract_package(test_class)
    prod_package = _java.extract_package(prod_class)

    if test_package != prod_package:
        msg = (
            "Test class {} in package {}, but class {} in package {}"
        ).format(test_class.name, test_package, prod_class.name, prod_package)
        raise ValueError(msg)

    return test_package


def run_test_class(
    test_class: pathlib.Path,
    prod_class: pathlib.Path,
    classpath: str,
    timeout: int,
    security_policy: Optional[pathlib.Path] = None,
) -> _output.TestResult:
    """Run a single test class on a single production class.

    Args:
        test_class: Path to a Java test class.
        prod_class: Path to a Java production class.
        classpath: A classpath to use in the tests.
        timeout: Maximum amount of time the test class is allowed to run, in
            seconds.
        security_policy: A JVM security policy to apply during test execution.
    Returns:
        Test results.
    """
    package = _extract_conforming_package(test_class, prod_class)

    prod_class_dir = _java.extract_package_root(prod_class, package)
    test_class_dir = _java.extract_package_root(test_class, package)

    test_class_name = _java.fqn_from_file(test_class)

    classpath = _java.generate_classpath(
        test_class_dir, prod_class_dir, classpath=classpath
    )

    command = ["java", "-enableassertions"]
    if security_policy:
        command += [
            "-Djava.security.manager",
            "-Djava.security.policy=={!s}".format(security_policy),
        ]
    command += [
        "-cp",
        classpath,
        "org.junit.runner.JUnitCore",
        test_class_name,
    ]

    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return _output.TestResult.build(test_class=test_class, proc=proc)
    except subprocess.TimeoutExpired as exc:
        return _output.TestResult.timed_out(
            test_class=test_class, timeout=exc.timeout
        )
