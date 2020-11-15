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
import pathlib
import re
from typing import Tuple, List, Union


import daiquiri

import repobee_plug as plug

from repobee_junit4 import _java
from repobee_junit4 import _junit4_runner
from repobee_junit4 import _exception
from repobee_junit4 import _output
from repobee_junit4 import SECTION
from repobee_junit4._generate_rtd import GenerateRTD  # noqa: F401

LOGGER = daiquiri.getLogger(__file__)

ResultPair = Tuple[pathlib.Path, pathlib.Path]

DEFAULT_TIMEOUT = 10

CLASSPATH = os.getenv("CLASSPATH") or ""


class JUnit4Hooks(plug.Plugin, plug.cli.CommandExtension):
    __settings__ = plug.cli.command_extension_settings(
        actions=[plug.cli.CoreCommand.repos.clone]
    )

    junit4_reference_tests_dir = plug.cli.option(
        help="path to a directory with reference tests",
        required=True,
        configurable=True,
    )

    junit4_ignore_tests = plug.cli.option(
        help="names of test classes to ignore", argparse_kwargs=dict(nargs="+")
    )

    junit4_hamcrest_path = plug.cli.option(
        help="absolute path to the hamcrest library",
        required=not re.search(_junit4_runner.JUNIT4_JAR_PATTERN, CLASSPATH),
        configurable=True,
    )

    junit4_junit_path = plug.cli.option(
        help="absolute path to the junit4 library",
        required=not re.search(_junit4_runner.JUNIT4_JAR_PATTERN, CLASSPATH),
        configurable=True,
    )

    junit4_disable_security = plug.cli.flag(
        help="disable the default security policy "
        "(student code can do whatever)"
    )

    verbosity = plug.cli.mutually_exclusive_group(
        junit4_verbose=plug.cli.flag(
            help="display more information about test failures"
        ),
        junit4_very_verbose=plug.cli.flag(
            help="display the full failure output, without truncating"
        ),
    )

    junit4_run_student_tests = plug.cli.flag(
        help="run test classes found in the student repos instead that match "
        "test classes from the reference tests directory"
    )

    junit4_timeout = plug.cli.option(
        help="maximum amount of seconds a test class is allowed to run "
        "before timing out",
        configurable=True,
        default=DEFAULT_TIMEOUT,
        converter=int,
    )

    def post_clone(
        self, repo: plug.StudentRepo, api: plug.PlatformAPI
    ) -> plug.Result:
        """Look for production classes in the student repo corresponding to
        test classes in the reference tests directory.

        Assumes that all test classes end in ``Test.java`` and that there is
        a directory with the same name as the master repo in the reference
        tests directory.

        Args:
            repo: A student repo.
            api: An instance of the platform API.
        Returns:
            a plug.Result specifying the outcome.
        """

        self._check_jars_exist()

        if not pathlib.Path(self.junit4_reference_tests_dir).is_dir():
            raise plug.PlugError(
                "{} is not a directory".format(self.junit4_reference_tests_dir)
            )
        assert self.args.assignments
        assert self.junit4_reference_tests_dir
        try:
            if not repo.path.exists():
                return plug.Result(
                    SECTION,
                    plug.Status.ERROR,
                    "student repo {!s} does not exist".format(repo.path),
                )

            compile_succeeded, compile_failed = self._compile_all(repo)
            test_results = self._run_tests(compile_succeeded)

            has_failures = compile_failed or any(
                map(lambda r: not r.success, test_results)
            )

            msg = _output.format_results(
                test_results,
                compile_failed,
                self.junit4_verbose,
                self.junit4_very_verbose,
            )

            status = (
                plug.Status.ERROR
                if compile_failed
                else (
                    plug.Status.WARNING
                    if has_failures
                    else plug.Status.SUCCESS
                )
            )
            return plug.Result(SECTION, status, msg)
        except _exception.ActError as exc:
            return exc.hook_result
        except Exception as exc:
            plug.log.exception("critical")
            return plug.Result(SECTION, plug.Status.ERROR, str(exc))

    def _compile_all(
        self, repo: plug.StudentRepo
    ) -> Tuple[List[ResultPair], List[plug.Result]]:
        """Attempt to compile all java files in the repo.

        Returns:
            a tuple of lists ``(succeeded, failed)``, where ``succeeded``
            are tuples on the form ``(test_class, prod_class)`` paths.
        """
        java_files = list(repo.path.rglob("*.java"))
        assignment_name = self._extract_assignment_name(repo.name)
        reference_test_classes = self._find_test_classes(assignment_name)
        test_classes = (
            _java.get_student_test_classes(repo.path, reference_test_classes)
            if self.junit4_run_student_tests
            else reference_test_classes
        )
        compile_succeeded, compile_failed = _java.pairwise_compile(
            test_classes, java_files, classpath=self._generate_classpath()
        )
        return compile_succeeded, compile_failed

    def _extract_assignment_name(self, repo_name: str) -> str:
        matches = list(filter(repo_name.endswith, self.args.assignments))

        if len(matches) == 1:
            return matches[0]
        else:
            msg = (
                "no assignment name matching the student repo"
                if not matches
                else "multiple matching master repo names: {}".format(
                    ", ".join(matches)
                )
            )
            res = plug.Result(SECTION, plug.Status.ERROR, msg)
            raise _exception.ActError(res)

    def _find_test_classes(self, assignment_name) -> List[pathlib.Path]:
        """Find all test classes (files ending in ``Test.java``) in directory
        at <reference_tests_dir>/<assignment_name>.

        Args:
            assignment_name: Name of an assignment.
        Returns:
            a list of test classes from the corresponding reference test
            directory.
        """
        test_dir = (
            pathlib.Path(self.junit4_reference_tests_dir) / assignment_name
        )
        if not test_dir.is_dir():
            res = plug.Result(
                SECTION,
                plug.Status.ERROR,
                "no reference test directory for {} in {}".format(
                    assignment_name, self.junit4_reference_tests_dir
                ),
            )
            raise _exception.ActError(res)

        test_classes = [
            file
            for file in test_dir.rglob("*.java")
            if file.name.endswith("Test.java")
            and file.name not in (self.junit4_ignore_tests or [])
        ]

        if not test_classes:
            res = plug.Result(
                SECTION,
                plug.Status.WARNING,
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
            classpath, active=not self.junit4_disable_security
        ) as security_policy:
            for test_class, prod_class in test_prod_class_pairs:
                test_result = _junit4_runner.run_test_class(
                    test_class,
                    prod_class,
                    classpath=classpath,
                    security_policy=security_policy,
                    timeout=self.junit4_timeout,
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
            self.junit4_hamcrest_path
            or re.search(_junit4_runner.HAMCREST_JAR_PATTERN, CLASSPATH)
        ):
            LOGGER.warning(warn.format("hamcrest"))
        if not (
            self.junit4_junit_path
            or re.search(_junit4_runner.JUNIT4_JAR_PATTERN, CLASSPATH)
        ):
            LOGGER.warning(warn.format("junit4"))

        paths = list(paths)
        if self.junit4_hamcrest_path:
            paths.append(self.junit4_hamcrest_path)
        if self.junit4_junit_path:
            paths.append(self.junit4_junit_path)
        return _java.generate_classpath(*paths, classpath=CLASSPATH)

    def _check_jars_exist(self):
        """Check that the specified jar files actually exist."""
        junit_path = self.junit4_junit_path or _parse_from_classpath(
            _junit4_runner.JUNIT4_JAR_PATTERN
        )
        hamcrest_path = self.junit4_hamcrest_path or _parse_from_classpath(
            _junit4_runner.HAMCREST_JAR_PATTERN
        )
        for raw_path in (junit_path, hamcrest_path):
            if not pathlib.Path(raw_path).is_file():
                raise plug.PlugError(
                    "{} is not a file, please check the filepath you "
                    "specified".format(raw_path)
                )


def _parse_from_classpath(
    pattern: Union[str, re.Pattern], classpath: str = CLASSPATH
) -> pathlib.Path:
    matches = re.search(pattern, classpath).groups()
    if not matches:
        raise plug.PlugError(
            f"expected to find match for '{pattern}' on the CLASSPATH variable"
        )
    return matches[0] if matches else None
