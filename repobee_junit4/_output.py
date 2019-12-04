"""Utility methods for processing and formatting output.

.. module:: _output
    :synopsis: Plugin that tries to compile all .java files in a repo.

.. moduleauthor:: Simon Larsén
"""
import sys
import os
import re
import collections
import pathlib
import subprocess
import math
from typing import Optional

from colored import bg, style

from repobee_junit4 import _java

SUCCESS_COLOR = bg("dark_green")
FAILURE_COLOR = bg("yellow")

DEFAULT_LINE_LENGTH_LIMIT = 150
DEFAULT_MAX_LINES = 10


class TestResult(
    collections.namedtuple(
        "TestResult",
        "fqn success num_failed num_passed test_failures timeout".split(),
    )
):
    """An immutable class for storing test results. Outside callers should use
    the static build methods :py:meth:`TestResult.build` or
    :py:meth:`TestResult.timed_out` to create instances.

    Attributes:
        fqn (str): The fully qualified name of the test class.
        success (bool): True if the test exited with a 0 exit status.
        num_failed (int): The amount of test cases that failed.
        num_passed (int): The amount of test cases that passed.
        test_failures (List[str]): A list of test failure messages.
        timeout (Optional[int]): The amount of seconds after which the test
            class timed out, or None if it did not time out.
    """

    @staticmethod
    def build(
        test_class: pathlib.Path, proc: subprocess.CompletedProcess
    ) -> "TestResult":
        """Build a TestResult.

        Args:
            test_class: Path to the test class.
            proc: A completed process of running the test class.
        Returns:
            A TestResult instance representing the test run.
        """
        stdout = proc.stdout.decode(encoding=sys.getdefaultencoding())
        return TestResult(
            fqn=_java.fqn_from_file(test_class),
            success=proc.returncode == 0,
            num_failed=_get_num_failed(stdout),
            num_passed=_get_num_passed(stdout),
            test_failures=_parse_failed_tests(stdout),
            timeout=None,
        )

    @staticmethod
    def timed_out(test_class: pathlib.Path, timeout: int):
        """Create a TestResult instance from a test that timed out.

        Args:
            test_class: Path to the test class.
            timeout: Amount of seconds after which the test class timed out.
        Returns:
            A TestResult instance representing the timed out test run.
        """
        return TestResult(
            fqn=_java.fqn_from_file(test_class),
            success=False,
            num_failed=0,
            num_passed=0,
            test_failures=list(),
            timeout=timeout,
        )

    def pretty_result(self, verbose: bool) -> str:
        """Format this test as a pretty-printed message."""
        title_color = SUCCESS_COLOR if self.success else FAILURE_COLOR
        msg = test_result_header(
            self.fqn,
            self.num_passed + self.num_failed,
            self.num_passed,
            title_color,
            self.timeout,
        )
        if not self.success and verbose:
            msg += os.linesep + os.linesep.join(self.test_failures)
        return msg


def _get_num_failed(test_output: str) -> int:
    """Get the amount of failed tests from the error output of JUnit4."""
    match = re.search(r"Failures: (\d+)", test_output)
    return int(match.group(1)) if match else 0


def _get_num_tests(test_output: str) -> int:
    """Get the total amount of tests. Only use this if there were test
    failures!
    """
    match = re.search(r"Tests run: (\d+)", test_output)
    return int(match.group(1)) if match else 0


def _get_num_passed(test_output: str) -> int:
    """Get the amount of passed tests from the output of JUnit4."""
    match = re.search(r"OK \((\d+) tests\)", test_output)
    if not match:  # there were failures
        return _get_num_tests(test_output) - _get_num_failed(test_output)
    return int(match.group(1))


def _parse_failed_tests(test_output: str) -> str:
    """Return a list of test failure descriptions, excluding stack traces."""
    return re.findall(
        r"^\d\) .*(?:\n(?!\s+at).*)*", test_output, flags=re.MULTILINE
    )


def test_result_header(
    test_class_name: str,
    num_tests: int,
    num_passed: int,
    title_color: bg,
    timeout: Optional[int] = None,
) -> str:
    """Return the header line for a test result."""
    if timeout is None:
        test_results = "Passed {}/{} tests".format(num_passed, num_tests)
    else:
        test_results = "Timed out after {} seconds".format(math.ceil(timeout))
    msg = "{}{}{}: {}".format(
        title_color, test_class_name, style.RESET, test_results
    )
    return msg


def format_results(test_results, compile_failed, verbose, very_verbose):
    def format_compile_error(res):
        msg = "{}Compile error:{} {}".format(bg("red"), style.RESET, res.msg)
        if very_verbose:
            return msg
        elif verbose:
            return _truncate_lines(msg)
        else:
            return msg.split("\n")[0]

    def format_test_result(res):
        msg = res.pretty_result(verbose or very_verbose)
        if very_verbose:
            return msg
        elif verbose:
            return _truncate_lines(msg, max_lines=sys.maxsize)
        else:
            return msg.split("\n")[0]

    compile_error_messages = list(map(format_compile_error, compile_failed))
    test_messages = list(map(format_test_result, test_results))
    msg = os.linesep.join(compile_error_messages + test_messages)
    if test_messages:
        num_passed = sum([res.num_passed for res in test_results])
        num_failed = sum([res.num_failed for res in test_results])
        total = num_passed + num_failed
        msg = (
            "Test summary: Passed {}/{} of all executed tests{}".format(
                num_passed, total, os.linesep
            )
            + msg
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
        lines = lines[: max_lines - 1] + [trunc_msg]
    return os.linesep.join(lines)
