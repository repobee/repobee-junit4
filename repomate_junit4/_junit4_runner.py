import pathlib
import tempfile
import re
import sys
import subprocess
import os
import contextlib
from typing import Tuple, Optional

import daiquiri

from repomate_plug import Status

from repomate_junit4 import _java


LOGGER = daiquiri.getLogger(__file__)
HAMCREST_JAR = "hamcrest-core-1.3.jar"
JUNIT_JAR = "junit-4.12.jar"

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
            "Security policy disabled, student code running without restrictions"
        )
        yield
        return

    with tempfile.NamedTemporaryFile() as security_policy_file:
        policy = _generate_default_security_policy(classpath)
        security_policy_file.write(policy.encode(encoding=sys.getdefaultencoding()))
        security_policy_file.flush()
        yield pathlib.Path(security_policy_file.name)


def _generate_default_security_policy(classpath: str) -> str:
    """Generate the default security policy from the classpath. ``junit-4.12.jar``
    must be on the classpath.
    """
    pattern = "{sep}([^{sep}]*{junit_jar}){sep}".format(
        sep=os.pathsep, junit_jar=JUNIT_JAR
    )
    junit_jar_matches = re.search(pattern, classpath)
    if not junit_jar_matches:
        raise ValueError("{} not on the classpath".format(JUNIT_JAR))
    path = junit_jar_matches.group(1)
    return _DEFAULT_SECURITY_POLICY_TEMPLATE.format(junit4_jar_path=path)


def get_num_failed(test_output: bytes) -> int:
    """Get the amount of failed tests from the error output of JUnit4."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"Failures: (\d+)", decoded)
    # TODO this is a bit unsafe, what if there is no match?
    return int(match.group(1))


def parse_failed_tests(test_output: bytes) -> str:
    """Return a list of test failure descriptions, excluding stack traces."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    return re.findall(r"^\d\) .*(?:\n(?!\s+at).*)*", decoded, flags=re.MULTILINE)


def _extract_conforming_package(test_class, prod_class):
    """Extract a package name from the test and production class.
    Raise if the test class and production class have different package
    statements.
    """
    test_package = _java.extract_package(test_class)
    prod_package = _java.extract_package(prod_class)

    if test_package != prod_package:
        msg = (
            "Test class {} in package {}, but production class {} in package {}"
        ).format(test_class.name, test_package, prod_class.name, prod_package)
        raise ValueError(msg)

    return test_package


def run_test_class(
    test_class: pathlib.Path,
    prod_class: pathlib.Path,
    classpath: str,
    verbose: bool = False,
    security_policy: Optional[pathlib.Path] = None,
) -> Tuple[str, str]:
    """Run a single test class on a single production class.

    Args:
        test_class: Path to a Java test class.
        prod_class: Path to a Java production class.
        classpath: A classpath to use in the tests.
        verbose: Whether to output more failure information.
    Returns:
        ()
    """
    package = _extract_conforming_package(test_class, prod_class)

    prod_class_dir = _java.extract_package_root(prod_class, package)
    test_class_dir = _java.extract_package_root(test_class, package)

    test_class_name = test_class.name[: -len(test_class.suffix)]  # remove .java
    test_class_name = _java.fqn(package, test_class_name)

    classpath = _java.generate_classpath(
        test_class_dir, prod_class_dir, classpath=classpath
    )

    command = ["java"]
    if security_policy:
        command += [
            "-Djava.security.manager",
            "-Djava.security.policy=={!s}".format(security_policy),
        ]
    command += ["-cp", classpath, "org.junit.runner.JUnitCore", test_class_name]

    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return _extract_results(proc, test_class_name, verbose)


def _extract_results(
    proc: subprocess.CompletedProcess, test_class_name: str, verbose: bool
) -> Tuple[str, str]:
    """Extract and format results from a completed test run."""
    if proc.returncode != 0:
        status = Status.ERROR
        msg = "Test class {} failed {} tests".format(
            test_class_name, get_num_failed(proc.stdout)
        )
        if verbose:
            msg += os.linesep + os.linesep.join(parse_failed_tests(proc.stdout))
    else:
        msg = "Test class {} passed!".format(test_class_name)
        status = Status.SUCCESS
    return status, msg
