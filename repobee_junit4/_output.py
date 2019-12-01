"""Utility methods for processing and formatting output.

.. module:: _output
    :synopsis: Plugin that tries to compile all .java files in a repo.

.. moduleauthor:: Simon Larsén
"""
import sys
import os
import re
import subprocess
import collections

from typing import Tuple

from repobee_plug import Status

from repobee_junit4 import _java


class TestResult(
    collections.namedtuple("TestResult", "test_class proc".split())
):
    @property
    def fqn(self):
        return _java.fqn_from_file(self.test_class)

    @property
    def success(self):
        return self.proc.returncode == 0

    @property
    def status(self):
        return Status.SUCCESS if self.success else Status.ERROR

    @property
    def num_failed(self):
        if self.success:
            return 0
        return get_num_failed(self.proc.stdout)

    @property
    def num_passed(self):
        if not self.success:
            return 0
        return get_num_passed(self.proc.stdout)

    @property
    def test_failures(self):
        return parse_failed_tests(self.proc.stdout)

    def pretty_result(self, verbose: bool) -> "TestResult":
        """Format this test as a pretty-printed message."""
        if not self.success:
            msg = "Test class {} failed {} tests".format(
                self.fqn, self.num_failed
            )
            if verbose:
                msg += os.linesep + os.linesep.join(self.test_failures)
        else:
            msg = "Test class {} passed all {} tests!".format(
                self.fqn, self.num_passed
            )
        return msg


def get_num_failed(test_output: bytes) -> int:
    """Get the amount of failed tests from the error output of JUnit4."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"Failures: (\d+)", decoded)
    # TODO this is a bit unsafe, what if there is no match?
    return int(match.group(1))


def get_num_passed(test_output: bytes) -> int:
    """Get the amount of passed tests from the output of JUnit4."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"OK \((\d+) tests\)", decoded)
    return int(match.group(1))


def parse_failed_tests(test_output: bytes) -> str:
    """Return a list of test failure descriptions, excluding stack traces."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    return re.findall(
        r"^\d\) .*(?:\n(?!\s+at).*)*", decoded, flags=re.MULTILINE
    )


def success_message(test_class: str, num_tests: int) -> str:
    """Generate a success message for the provided test class.

    Args:
        test_class: Fully qualified name of the test class.
        num_tests: Amount of tests that were run.
    Returns:
        A success message.
    """
    return "Test class {} passed all {} tests!".format(test_class, num_tests)


def failure_message(test_class: str, num_failed: int, num_tests: int) -> str:
    """Generate a failure message for the provided test class.

    Args:
        test_class: Fully qualified name of the test class.
        num_failed: The amount of tests that failed.
        num_tests: The total amount of tests that were run.
    Returns:
        A failure message.
    """
    return "Test class {} failed {} ouf of {} tests".format(
        test_class, num_failed, num_tests
    )
