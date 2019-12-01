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
FAILURE_COLOR = bg("yellow")

DEFAULT_LINE_LENGTH_LIMIT = 150
DEFAULT_MAX_LINES = 5


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
        title_color = SUCCESS_COLOR if self.success else FAILURE_COLOR
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


def format_results(test_results, compile_failed, verbose, very_verbose):
    compile_error_messages = [
        "{}Compile error:{} {}".format(bg("red"), style.RESET, res.msg)
        for res in compile_failed
    ]
    test_messages = [
        res.pretty_result(verbose or very_verbose) for res in test_results
    ]

    msg = os.linesep.join(
        [
            msg if very_verbose else _truncate_lines(msg)
            for msg in compile_error_messages + test_messages
        ]
    )
    if test_messages:
        num_passed = sum([res.num_passed for res in test_results])
        num_failed = sum([res.num_failed for res in test_results])
        total = num_passed + num_failed
        msg = (
            "Passed {}/{} tests{}".format(num_passed, total, os.linesep) + msg
        )
    return msg


def _truncate_lines(
    string: str,
    max_len: int = DEFAULT_LINE_LENGTH_LIMIT,
    max_lines: int = DEFAULT_MAX_LINES,
):
    """Truncate lines to max_len characters."""
    trunc_msg = " #[...]# "
    if max_len <= len(trunc_msg):
        raise ValueError(
            "max_len must be greater than {}".format(len(trunc_msg))
        )

    effective_len = max_len - len(trunc_msg)
    head_len = effective_len // 2
    tail_len = effective_len // 2

    def truncate(s):
        if len(s) > max_len:
            return s[:head_len] + trunc_msg + s[-tail_len:]
        return s

    lines = [truncate(line) for line in string.split(os.linesep)]
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [trunc_msg]
    return os.linesep.join(lines)
