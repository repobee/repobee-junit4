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

TestResult = collections.namedtuple("TestResult", "")


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


def extract_results(
    proc: subprocess.CompletedProcess, test_class: str, verbose: bool
) -> Tuple[str, str]:
    """Extract and format results from a completed test run."""
    if proc.returncode != 0:
        status = Status.ERROR
        msg = "Test class {} failed {} tests".format(
            test_class, get_num_failed(proc.stdout)
        )
        if verbose:
            msg += os.linesep + os.linesep.join(
                parse_failed_tests(proc.stdout)
            )
    else:
        msg = "Test class {} passed all {} tests!".format(
            test_class, get_num_passed(proc.stdout)
        )
        status = Status.SUCCESS
    return status, msg
