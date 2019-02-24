import pathlib
import re
import sys
import subprocess
import os

from typing import Tuple

from repomate_plug import Status

from repomate_junit4 import _java


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
    command = ["java", "-cp", classpath, "org.junit.runner.JUnitCore", test_class_name]
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
