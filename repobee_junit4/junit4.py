"""Plugin that runs JUnit4 on test classes and corresponding production
classes.

.. important::

    Requires ``javac`` and ``java`` to be installed, and having
    ``hamcrest-core-1.3.jar`` and ``junit-4.12.jar`` on the local macine.

This plugin performs a fairly complicated tasks of running test classes from
pre-specified reference tests on production classes that are dynamically
discovered in student repositories. See the README for more details.

.. module:: javac
    :synopsis: Plugin that tries to compile all .java files in a repo.

.. moduleauthor:: Simon Larsén
"""
import itertools
import os
import argparse
import configparser
import pathlib
import collections
from typing import Union, Iterable, Tuple, List, Any


import daiquiri
from colored import bg, style

import repobee_plug as plug
from repobee_plug import Status

from repobee_junit4 import _java
from repobee_junit4 import _junit4_runner
from repobee_junit4 import SECTION

LOGGER = daiquiri.getLogger(__file__)

ResultPair = Tuple[pathlib.Path, pathlib.Path]

DEFAULT_LINE_LIMIT = 150


class _ActException(Exception):
    """Raise if something goes wrong in act_on_clone_repo."""

    def __init__(self, hook_result):
        self.hook_result = hook_result


class JUnit4Hooks(plug.Plugin):
    def __init__(self):
        self._master_repo_names = []
        self._reference_tests_dir = ""
        self._ignore_tests = []
        self._hamcrest_path = ""
        self._junit_path = ""
        self._classpath = os.getenv("CLASSPATH") or ""
        self._verbose = False
        self._very_verbose = False
        self._disable_security = False
        self._run_student_tests = False

    def act_on_cloned_repo(
        self, path: Union[str, pathlib.Path]
    ) -> plug.HookResult:
        """Look for production classes in the student repo corresponding to
        test classes in the reference tests directory.

        Assumes that all test classes end in ``Test.java`` and that there is
        a directory with the same name as the master repo in the reference
        tests directory.

        Args:
            path: Path to the student repo.
        Returns:
            a plug.HookResult specifying the outcome.
        """
        if not pathlib.Path(self._reference_tests_dir).is_dir():
            raise plug.exception.PlugError(
                "{} is not a directory".format(self._reference_tests_dir)
            )
        assert self._master_repo_names
        assert self._reference_tests_dir
        try:
            path = pathlib.Path(path)
            if not path.exists():
                return plug.HookResult(
                    SECTION,
                    Status.ERROR,
                    "student repo {!s} does not exist".format(path),
                )

            compile_succeeded, compile_failed = self._compile_all(path)
            tests_succeeded, tests_failed = self._run_tests(compile_succeeded)

            msg = self._format_results(
                itertools.chain(tests_succeeded, tests_failed, compile_failed)
            )

            status = (
                Status.ERROR
                if tests_failed or compile_failed
                else Status.SUCCESS
            )
            return plug.HookResult(SECTION, status, msg)
        except _ActException as exc:
            return exc.hook_result
        except Exception as exc:
            return plug.HookResult(SECTION, Status.ERROR, str(exc))

    def parse_args(self, args: argparse.Namespace) -> None:
        """Get command line arguments.

        Args:
            args: The full namespace returned by
            :py:func:`argparse.ArgumentParser.parse_args`
        """
        self._master_repo_names = args.master_repo_names
        self._reference_tests_dir = (
            args.reference_tests_dir
            if args.reference_tests_dir
            else self._reference_tests_dir
        )
        self._ignore_tests = (
            args.ignore_tests if args.ignore_tests else self._ignore_tests
        )
        self._hamcrest_path = (
            args.hamcrest_path if args.hamcrest_path else self._hamcrest_path
        )
        self._junit_path = (
            args.junit_path if args.junit_path else self._junit_path
        )
        self._verbose = args.verbose
        self._very_verbose = args.very_verbose
        self._disable_security = (
            args.disable_security
            if args.disable_security
            else self._disable_security
        )
        self._run_student_tests = args.run_student_tests

    def clone_parser_hook(
        self, clone_parser: configparser.ConfigParser
    ) -> None:
        """Add reference_tests_dir argument to parser.

        Args:
            clone_parser: The ``clone`` subparser.
        """
        clone_parser.add_argument(
            "--junit4-reference-tests-dir",
            help="Path to a directory with reference tests.",
            type=str,
            dest="reference_tests_dir",
            required=not self._reference_tests_dir,
        )

        clone_parser.add_argument(
            "--junit4-ignore-tests",
            help="Names of test classes to ignore.",
            type=str,
            dest="ignore_tests",
            nargs="+",
        )

        clone_parser.add_argument(
            "--junit4-hamcrest-path",
            help="Absolute path to the `{}` library.".format(
                _junit4_runner.HAMCREST_JAR
            ),
            type=str,
            dest="hamcrest_path",
            # required if not picked up in config_hook nor on classpath
            required=not self._hamcrest_path
            and _junit4_runner.HAMCREST_JAR not in self._classpath,
        )

        clone_parser.add_argument(
            "--junit4-junit-path",
            help="Absolute path to the `{}` library.".format(
                _junit4_runner.JUNIT_JAR
            ),
            type=str,
            dest="junit_path",
            # required if not picked up in config_hook nor on classpath
            required=not self._junit_path
            and _junit4_runner.JUNIT_JAR not in self._classpath,
        )

        clone_parser.add_argument(
            "--junit4-disable-security",
            help=(
                "Disable the default security policy (student code can do "
                "whatever)."
            ),
            dest="disable_security",
            action="store_true",
        )

        verbosity = clone_parser.add_mutually_exclusive_group()
        verbosity.add_argument(
            "--junit4-verbose",
            help="Display more information about test failures.",
            dest="verbose",
            action="store_true",
        )
        verbosity.add_argument(
            "--junit4-very-verbose",
            help="Display the full failure output, without truncating.",
            dest="very_verbose",
            action="store_true",
        )

        clone_parser.add_argument(
            "--junit4-run-student-tests",
            help="Run test classes found in the student repos instead of "
            "those from the reference tests directory. Only tests that exist "
            "in the reference tests directory will be searched for.",
            dest="run_student_tests",
            action="store_true",
        )

    def config_hook(self, config_parser: configparser.ConfigParser) -> None:
        """Look for hamcrest and junit paths in the config, and get the classpath.

        Args:
            config: the config parser after config has been read.
        """
        self._hamcrest_path = config_parser.get(
            SECTION, "hamcrest_path", fallback=self._hamcrest_path
        )
        self._junit_path = config_parser.get(
            SECTION, "junit_path", fallback=self._junit_path
        )
        self._reference_tests_dir = config_parser.get(
            SECTION, "reference_tests_dir", fallback=self._reference_tests_dir
        )

    def _compile_all(
        self, path: pathlib.Path
    ) -> Tuple[List[ResultPair], List[plug.HookResult]]:
        """Attempt to compile all java files in the repo.

        Returns:
            a tuple of lists ``(succeeded, failed)``, where ``succeeded``
            are tuples on the form ``(test_class, prod_class)`` paths.
        """
        java_files = list(path.rglob("*.java"))
        master_name = self._extract_master_repo_name(path)
        reference_test_classes = self._find_test_classes(master_name)
        test_classes = (
            self._find_matching_files(path, reference_test_classes)
            if self._run_student_tests
            else reference_test_classes
        )
        compile_succeeded, compile_failed = _java.pairwise_compile(
            test_classes, java_files, classpath=self._generate_classpath()
        )
        return compile_succeeded, compile_failed

    def _extract_master_repo_name(self, path: pathlib.Path) -> str:
        """Extract the master repo name from the student repo at ``path``. For
        this to work, the corresponding master repo name must be in
        self._master_repo_names.

        Args:
            path: path to the student repo
        Returns:
            the name of the associated master repository
        """
        matches = list(filter(path.name.endswith, self._master_repo_names))

        if len(matches) == 1:
            return matches[0]
        else:
            msg = (
                "no master repo name matching the student repo"
                if not matches
                else "multiple matching master repo names: {}".format(
                    ", ".join(matches)
                )
            )
            res = plug.HookResult(SECTION, Status.ERROR, msg)
            raise _ActException(res)

    def _find_test_classes(self, master_name) -> List[pathlib.Path]:
        """Find all test classes (files ending in ``Test.java``) in directory
        at <reference_tests_dir>/<master_name>.

        Args:
            master_name: Name of a master repo.
        Returns:
            a list of test classes from the corresponding reference test
            directory.
        """
        test_dir = pathlib.Path(self._reference_tests_dir) / master_name
        if not test_dir.is_dir():
            res = plug.HookResult(
                SECTION,
                Status.ERROR,
                "no reference test directory for {} in {}".format(
                    master_name, self._reference_tests_dir
                ),
            )
            raise _ActException(res)

        test_classes = [
            file
            for file in test_dir.rglob("*.java")
            if file.name.endswith("Test.java")
            and file.name not in self._ignore_tests
        ]

        if not test_classes:
            res = plug.HookResult(
                SECTION,
                Status.WARNING,
                "no files ending in `Test.java` found in {!s}".format(
                    test_dir
                ),
            )
            raise _ActException(res)

        return test_classes

    def _find_matching_files(
        self, path: pathlib.Path, reference_files: List[pathlib.Path]
    ) -> List[pathlib.Path]:
        """Return paths to all files that match filenames in the provided list.
        Raises if there is more than one or no matches for any of the files.
        """
        filenames = {f.name for f in reference_files}
        return [file for file in path.rglob("*") if file.name in filenames]

    def _format_results(self, hook_results: Iterable[plug.HookResult]):
        """Format a list of plug.HookResult tuples as a nice string.

        Args:
            hook_results: A list of plug.HookResult tuples.
        Returns:
            a formatted string
        """
        backgrounds = {
            Status.ERROR: bg("red"),
            Status.WARNING: bg("yellow"),
            Status.SUCCESS: bg("dark_green"),
        }

        def test_result_string(status, msg):
            return "{}{}:{} {}".format(
                backgrounds[status],
                status,
                style.RESET,
                _truncate_lines(msg) if self._verbose else msg,
            )

        return os.linesep.join(
            [
                test_result_string(status, msg)
                for _, status, msg, _ in hook_results
            ]
        )

    def _run_tests(
        self, test_prod_class_pairs: ResultPair
    ) -> Tuple[List[plug.HookResult], List[plug.HookResult]]:
        """Run tests and return the results.

        Args:
            test_prod_class_pairs: A list of tuples on the form
            ``(test_class_path, prod_class_path)``

        Returns:
            A tuple of lists ``(succeeded, failed)`` containing HookResult
            tuples.
        """
        succeeded = []
        failed = []
        classpath = self._generate_classpath()
        with _junit4_runner.security_policy(
            classpath, active=not self._disable_security
        ) as security_policy:
            for test_class, prod_class in test_prod_class_pairs:
                status, msg = _junit4_runner.run_test_class(
                    test_class,
                    prod_class,
                    classpath=classpath,
                    verbose=self._verbose or self._very_verbose,
                    security_policy=security_policy,
                )
                if status != Status.SUCCESS:
                    failed.append(plug.HookResult(SECTION, status, msg))
                else:
                    succeeded.append(plug.HookResult(SECTION, status, msg))
            return succeeded, failed

    def _generate_classpath(self, *paths: pathlib.Path) -> str:
        """
        Args:
            paths: One or more paths to add to the classpath.
        Returns:
            a formated classpath to be used with ``java`` and ``javac``
        """
        warn = (
            "`{}` is not configured and not on the CLASSPATH variable."
            "This will probably crash."
        )
        if not (
            self._hamcrest_path
            or _junit4_runner.HAMCREST_JAR in self._classpath
        ):
            LOGGER.warning(warn.format(_junit4_runner.HAMCREST_JAR))
        if not (
            self._junit_path or _junit4_runner.JUNIT_JAR in self._classpath
        ):
            LOGGER.warning(warn.format(_junit4_runner.JUNIT_JAR))

        paths = list(paths)
        if self._hamcrest_path:
            paths.append(self._hamcrest_path)
        if self._junit_path:
            paths.append(self._junit_path)
        return _java.generate_classpath(*paths, classpath=self._classpath)


def _truncate_lines(string: str, max_len: int = DEFAULT_LINE_LIMIT):
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

    return os.linesep.join(
        [truncate(line) for line in string.split(os.linesep)]
    )
