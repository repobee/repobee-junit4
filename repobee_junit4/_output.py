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

from colored import bg, style


SUCCESS_COLOR = bg("dark_green")
FAILURE_COLOR = bg("red")


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
        return _get_num_failed(self.proc.stdout)

    @property
    def num_passed(self):
        return _get_num_passed(self.proc.stdout)

    @property
    def test_failures(self):
        return _parse_failed_tests(self.proc.stdout)

    def pretty_result(self, verbose: bool) -> str:
        """Format this test as a pretty-printed message."""
        title_color = bg("dark_green") if self.success else bg("red")
        num_passed = self.num_passed
        num_failed = self.num_failed
        msg = test_result_header(
            self.fqn, num_passed + num_failed, num_passed, title_color
        )
        if not self.success and verbose:
            msg += os.linesep + os.linesep.join(self.test_failures)
        return msg


def _get_num_failed(test_output: bytes) -> int:
    """Get the amount of failed tests from the error output of JUnit4."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"Failures: (\d+)", decoded)
    return int(match.group(1)) if match else 0


def _get_num_tests(test_output: bytes) -> int:
    """Get the total amount of tests. Only use this if there were test failures!"""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"Tests run: (\d+)", decoded)
    return int(match.group(1)) if match else 0


def _get_num_passed(test_output: bytes) -> int:
    """Get the amount of passed tests from the output of JUnit4."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r"OK \((\d+) tests\)", decoded)
    if not match:  # there were failures
        return _get_num_tests(test_output) - _get_num_failed(test_output)
    return int(match.group(1))


def _parse_failed_tests(test_output: bytes) -> str:
    """Return a list of test failure descriptions, excluding stack traces."""
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    return re.findall(
        r"^\d\) .*(?:\n(?!\s+at).*)*", decoded, flags=re.MULTILINE
    )


def test_result_header(
    test_class_name: str, num_tests: int, num_passed: int, title_color: bg
) -> str:
    """Return the header line for a test result."""
    test_results = "Passed {}/{} tests".format(num_passed, num_tests)
    msg = "{}{}{}: {}".format(
        title_color, test_class_name, style.RESET, test_results,
    )
    return msg
