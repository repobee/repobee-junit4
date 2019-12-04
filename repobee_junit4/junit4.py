"""Plugin that runs JUnit4 on test classes and corresponding production
classes.

.. important::

    Requires ``javac`` and ``java`` to be installed, and having
    ``hamcrest-core-1.3.jar`` and ``junit-4.12.jar`` on the local macine.

This plugin performs a fairly complicated tasks of running test classes from
pre-specified reference tests on production classes that are dynamically
discovered in student repositories. See the README for more details.

.. module:: junit4
    :synopsis: Plugin that runts JUnit4 test classes on students' production
        code.

.. moduleauthor:: Simon Larsén
"""
import os
import argparse
import configparser
import pathlib
from typing import Union, Tuple, List


import daiquiri

import repobee_plug as plug
from repobee_plug import Status

from repobee_junit4 import _java
from repobee_junit4 import _junit4_runner
from repobee_junit4 import _exception
from repobee_junit4 import _output
from repobee_junit4 import SECTION

LOGGER = daiquiri.getLogger(__file__)

ResultPair = Tuple[pathlib.Path, pathlib.Path]

DEFAULT_TIMEOUT = 10


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
        self._timeout = DEFAULT_TIMEOUT

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
            test_results = self._run_tests(compile_succeeded)

            has_failures = compile_failed or any(
                map(lambda r: not r.success, test_results)
            )

            msg = _output.format_results(
                test_results, compile_failed, self._verbose, self._very_verbose
            )

            status = (
                Status.ERROR
                if compile_failed
                else (Status.WARNING if has_failures else Status.SUCCESS)
            )
            return plug.HookResult(SECTION, status, msg)
        except _exception.ActError as exc:
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
            args.junit4_reference_tests_dir
            if args.junit4_reference_tests_dir
            else self._reference_tests_dir
        )
        self._ignore_tests = (
            args.junit4_ignore_tests
            if args.junit4_ignore_tests
            else self._ignore_tests
        )
        self._hamcrest_path = (
            args.junit4_hamcrest_path
            if args.junit4_hamcrest_path
            else self._hamcrest_path
        )
        self._junit_path = (
            args.junit4_junit_path
            if args.junit4_junit_path
            else self._junit_path
        )
        self._verbose = args.junit4_verbose
        self._very_verbose = args.junit4_very_verbose
        self._disable_security = (
            args.junit4_disable_security
            if args.junit4_disable_security
            else self._disable_security
        )
        self._run_student_tests = args.junit4_run_student_tests
        self._timeout = args.junit4_timeout
        # at this point, the jars must have been specified and exist
        self._check_jars_exist()

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
            dest="junit4_reference_tests_dir",
            required=not self._reference_tests_dir,
        )

        clone_parser.add_argument(
            "--junit4-ignore-tests",
            help="Names of test classes to ignore.",
            type=str,
            dest="junit4_ignore_tests",
            nargs="+",
        )

        clone_parser.add_argument(
            "--junit4-hamcrest-path",
            help="Absolute path to the `{}` library.".format(
                _junit4_runner.HAMCREST_JAR
            ),
            type=str,
            dest="junit4_hamcrest_path",
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
            dest="junit4_junit_path",
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
            dest="junit4_disable_security",
            action="store_true",
        )

        verbosity = clone_parser.add_mutually_exclusive_group()
        verbosity.add_argument(
            "--junit4-verbose",
            help="Display more information about test failures.",
            dest="junit4_verbose",
            action="store_true",
        )
        verbosity.add_argument(
            "--junit4-very-verbose",
            help="Display the full failure output, without truncating.",
            dest="junit4_very_verbose",
            action="store_true",
        )

        clone_parser.add_argument(
            "--junit4-run-student-tests",
            help="Run test classes found in the student repos instead of "
            "those from the reference tests directory. Only tests that exist "
            "in the reference tests directory will be searched for.",
            dest="junit4_run_student_tests",
            action="store_true",
        )

        clone_parser.add_argument(
            "--junit4-timeout",
            help="Maximum amount of seconds a test class is allowed to run "
            "before timing out.",
            dest="junit4_timeout",
            type=int,
            default=self._timeout,
        )

    def config_hook(self, config_parser: configparser.ConfigParser) -> None:
        """Look for hamcrest and junit paths in the config, and get the classpath.

        Args:
            config: the config parser after config has been read.
        """
        if SECTION not in config_parser:
            return
        self._hamcrest_path = config_parser.get(
            SECTION, "hamcrest_path", fallback=self._hamcrest_path
        )
        self._junit_path = config_parser.get(
            SECTION, "junit_path", fallback=self._junit_path
        )
        self._reference_tests_dir = config_parser.get(
            SECTION, "reference_tests_dir", fallback=self._reference_tests_dir
        )
        if "timeout" in config_parser[SECTION]:
            timeout = config_parser.get(SECTION, "timeout")
            if not timeout.isnumeric():
                raise plug.PlugError(
                    "config value timeout in section [{}] must be an integer, but was: {}".format(
                        SECTION, timeout
                    )
                )
        self._timeout = int(
            config_parser.get(SECTION, "timeout", fallback=str(self._timeout))
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
            _java.get_student_test_classes(path, reference_test_classes)
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
            raise _exception.ActError(res)

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
            raise _exception.ActError(res)

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
            raise _exception.ActError(res)

        return test_classes

    def _run_tests(
        self, test_prod_class_pairs: ResultPair
    ) -> _output.TestResult:
        """Run tests and return the results.

        Args:
            test_prod_class_pairs: A list of tuples on the form
            ``(test_class_path, prod_class_path)``

        Returns:
            A TestResult for each test class run.
        """
        results = []
        classpath = self._generate_classpath()
        with _junit4_runner.security_policy(
            classpath, active=not self._disable_security
        ) as security_policy:
            for test_class, prod_class in test_prod_class_pairs:
                test_result = _junit4_runner.run_test_class(
                    test_class,
                    prod_class,
                    classpath=classpath,
                    security_policy=security_policy,
                    timeout=self._timeout,
                )
                results.append(test_result)
            return results

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

    def _check_jars_exist(self):
        """Check that the specified jar files actually exist."""
        junit_path = self._junit_path or self._parse_from_classpath(
            _junit4_runner.JUNIT_JAR
        )
        hamcrest_path = self._hamcrest_path or self._parse_from_classpath(
            _junit4_runner.HAMCREST_JAR
        )
        for raw_path in (junit_path, hamcrest_path):
            if not pathlib.Path(raw_path).is_file():
                raise plug.PlugError(
                    "{} is not a file, please check the filepath you "
                    "specified".format(raw_path)
                )

    def _parse_from_classpath(self, filename: str) -> pathlib.Path:
        """Parse the full path to the given filename from the classpath, if
        it's on the classpath at all. If there are several hits, take the first
        one, and if there are none, raise a PlugError.
        """
        matches = [
            pathlib.Path(p)
            for p in self._classpath.split(os.pathsep)
            if p.endswith(filename)
        ]
        if not matches:
            raise plug.PlugError(
                "expected to find {} on the CLASSPATH variable".format(
                    filename
                )
            )
        return matches[0] if matches else None
