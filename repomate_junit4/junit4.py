"""Plugin that runs JUnit4 on test classes and corresponding production classes.

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
import subprocess
import itertools
import sys
import os
import argparse
import configparser
import re
import pathlib
from typing import Union, Iterable, Tuple, List

import daiquiri
from colored import bg, style

import repomate_plug as plug
from repomate_plug import Status

LOGGER = daiquiri.getLogger(__file__)

SECTION = "junit4"

HAMCREST_JAR = "hamcrest-core-1.3.jar"
JUNIT_JAR = "junit-4.12.jar"

ResultPair = Tuple[pathlib.Path, pathlib.Path]


class _ActException(Exception):
    """Raise if something goes wrong in act_on_clone_repo."""

    def __init__(self, hook_result):
        self.hook_result = hook_result


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


class JUnit4Hooks(plug.Plugin):
    def __init__(self):
        self._master_repo_names = []
        self._reference_tests_dir = ""
        self._ignore_tests = []
        self._hamcrest_path = ""
        self._junit_path = ""
        self._classpath = ""

    def act_on_cloned_repo(self, path: Union[str, pathlib.Path]) -> plug.HookResult:
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

            status = Status.ERROR if tests_failed or compile_failed else Status.SUCCESS
            return plug.HookResult(SECTION, status, msg)
        except _ActException as exc:
            return exc.hook_result

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
        self._junit_path = args.junit_path if args.junit_path else self._junit_path
        self._verbose = args.verbose

    def clone_parser_hook(self, clone_parser: configparser.ConfigParser) -> None:
        """Add reference_tests_dir argument to parser.

        Args:
            clone_parser: The ``clone`` subparser.
        """
        clone_parser.add_argument(
            "-rtd",
            "--reference-tests-dir",
            help="Path to a directory with reference tests.",
            type=str,
            required=not self._reference_tests_dir,
        )

        clone_parser.add_argument(
            "-i",
            "--ignore-tests",
            help="Names of test classes to ignore.",
            type=str,
            nargs="+",
        )

        clone_parser.add_argument(
            "-ham",
            "--hamcrest-path",
            help="Absolute path to the `{}` library.".format(HAMCREST_JAR),
            type=str,
            # required if not picked up in config_hook nor on classpath
            required=not self._hamcrest_path and not HAMCREST_JAR in self._classpath,
        )

        clone_parser.add_argument(
            "-junit",
            "--junit-path",
            help="Absolute path to the `{}` library.".format(JUNIT_JAR),
            type=str,
            # required if not picked up in config_hook nor on classpath
            required=not self._junit_path and not JUNIT_JAR in self._classpath,
        )

        clone_parser.add_argument(
            "-v",
            "--verbose",
            help="Display more information about test failures.",
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
        self._classpath = os.getenv("CLASSPATH") or ""

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
        test_classes = self._find_test_classes(master_name)
        status, msg = self._javac(java_files)

        if status != Status.SUCCESS:
            raise _ActException(plug.HookResult(SECTION, status, msg))

        compile_succeeded, compile_failed = self._compile(test_classes, java_files)
        return compile_succeeded, compile_failed

    def _extract_master_repo_name(self, path: pathlib.Path) -> str:
        """Extract the master repo name from the student repo at ``path``. For
        this to work, the corresponding master repo name must be in
        self._master_repo_names.

        Args:
            path: path to the student repo.
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
                else "multiple master repo names matching student repo: {}".format(
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
            a list of test classes from the corresponding reference test directory.
        """
        test_dir = pathlib.Path(self._reference_tests_dir) / master_name
        if not (test_dir.exists() and test_dir.is_dir()):
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
            if file.name.endswith("Test.java") and file.name not in self._ignore_tests
        ]

        if not test_classes:
            res = plug.HookResult(
                SECTION,
                Status.WARNING,
                "no files ending in `Test.java` found in {!s}".format(test_dir),
            )
            raise _ActException(res)

        return test_classes

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
        test_result_string = lambda status, msg: "{}{}:{} {}".format(
            backgrounds[status], status, style.RESET, msg
        )
        return os.linesep.join(
            [test_result_string(status, msg) for _, status, msg in hook_results]
        )

    def _compile(
        self, test_classes: List[pathlib.Path], java_files: List[pathlib.Path]
    ) -> Tuple[List[plug.HookResult], List[plug.HookResult]]:
        """Compile test classes with their associated production classes.

        For each test class:
            
            1. Find the associated production class among the ``java_files``
            2. Compile the test class together with all of the .java files in
            the associated production class' directory.
        
        Args:
            test_classes: A list of paths to test classes.
            java_files: A list of paths to java files from the student repo.
        Returns:
            A tuple of lists of HookResults on the form ``(succeeded, failed)``
        """

        failed = []
        succeeded = []
        # only use concrete test classes
        concrete_test_classes = filter(
            lambda t: not self._is_abstract_class(t), test_classes
        )
        for test_class in concrete_test_classes:
            package = _extract_package(test_class)
            prod_class_name = test_class.name.replace("Test.java", ".java")
            try:
                prod_class_path = [
                    file
                    for file in java_files
                    if file.name == prod_class_name
                    and _extract_package(file) == package
                ][0]
                adjacent_java_files = [
                    file
                    for file in prod_class_path.parent.glob("*.java")
                    if not file.name.endswith("Test.java")
                ] + list(test_class.parent.glob("*Test.java"))
                status, msg = self._javac([*adjacent_java_files])
                if status != Status.SUCCESS:
                    failed.append(plug.HookResult(SECTION, status, msg))
                else:
                    succeeded.append((test_class, prod_class_path))
            except IndexError as exc:
                failed.append(
                    plug.HookResult(
                        SECTION,
                        Status.ERROR,
                        "no production class found for "
                        + _fqn(package, test_class.name),
                    )
                )

        return succeeded, failed

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
        for test_class, prod_class in test_prod_class_pairs:
            status, msg = self._junit(test_class, prod_class)
            if status != Status.SUCCESS:
                failed.append(plug.HookResult(SECTION, status, msg))
            else:
                succeeded.append(plug.HookResult(SECTION, status, msg))
        return succeeded, failed

    def _is_abstract_class(self, test_class: pathlib.Path) -> bool:
        """Check if the file is an abstract class."""
        assert test_class.name.endswith(".java")
        regex = r"^\s*?(public\s+)?abstract\s+class\s+{}".format(test_class.name[:-5])
        match = re.search(
            regex,
            test_class.read_text(encoding=sys.getdefaultencoding()),
            flags=re.MULTILINE,
        )
        return match is not None

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
        classpath = self._classpath
        for path in paths:
            classpath += ":{!s}".format(path)

        if not (self._hamcrest_path or HAMCREST_JAR in classpath):
            LOGGER.warning(warn.format(HAMCREST_JAR))
        if not (self._junit_path or JUNIT_JAR in classpath):
            LOGGER.warning(warn.format(JUNIT_JAR))

        if self._hamcrest_path:
            classpath += ":{}".format(self._hamcrest_path)
        if self._junit_path:
            classpath += ":{}".format(self._junit_path)
        classpath += ":."
        return classpath

    @staticmethod
    def _extract_valid_package(test_class, prod_class):
        """Extract a package name from the test and production class.
        Raise if the test class and production class have different package
        statements.
        """
        test_package = _extract_package(test_class)
        prod_package = _extract_package(prod_class)

        if test_package != prod_package:
            msg = (
                "Test class {} in package {}, but production class {} in package {}"
            ).format(test_class.name, test_package, prod_class.name, prod_package)
            raise _ActException(plug.HookResult(SECTION, Status.ERROR, msg))

        return test_package

    def _junit(self, test_class, prod_class):
        package = self._extract_valid_package(test_class, prod_class)

        prod_class_dir = _package_root(prod_class, package)
        test_class_dir = _package_root(test_class, package)

        test_class_name = test_class.name[: -len(test_class.suffix)]  # remove .java
        test_class_name = _fqn(package, test_class_name)

        classpath = self._generate_classpath(test_class_dir, prod_class_dir)
        command = [
            "java",
            "-cp",
            classpath,
            "org.junit.runner.JUnitCore",
            test_class_name,
        ]
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            status = Status.ERROR
            msg = "Test class {} failed {} tests".format(
                test_class_name, get_num_failed(proc.stdout)
            )
            if self._verbose:
                msg += os.linesep + os.linesep.join(parse_failed_tests(proc.stdout))
        else:
            msg = "Test class {} passed!".format(test_class_name)
            status = Status.SUCCESS

        return status, msg

    def _javac(self, java_files: Iterable[Union[str, pathlib.Path]]) -> Tuple[str, str]:
        """Run ``javac`` on all of the specified files, assuming that they are
        all ``.java`` files.

        Args:
            java_files: paths to ``.java`` files.
        Returns:
            (status, msg), where status is e.g. :py:const:`Status.ERROR` and
            the message describes the outcome in plain text.
        """
        classpath = self._generate_classpath()
        command = ["javac", "-cp", classpath, *[str(path) for path in java_files]]
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            status = Status.ERROR
            msg = proc.stderr.decode(sys.getdefaultencoding())
        else:
            msg = "all files compiled successfully"
            status = Status.SUCCESS

        return status, msg


def _package_root(class_: pathlib.Path, package: str) -> pathlib.Path:
    """Return the package root, given that class_ is the path to a .java file.
    If the package is the default package (empty string), simply return a copy
    of class_.

    Raise if the directory structure doesn't correspond to the package
    statement.
    """
    _check_directory_corresponds_to_package(class_.parent, package)
    root = class_.parent
    if package:
        root = class_.parents[len(package.split("."))]
    return root


def _extract_package(class_: pathlib.Path) -> str:
    """Return the name package of the class. An empty string
    denotes the default package.
    """
    assert class_.name.endswith(".java")
    # yes, $ is a valid character for a Java identifier ...
    ident = r"[\w$][\w\d_$]*"
    regex = r"^\s*?package\s+({ident}(.{ident})*);".format(ident=ident)
    with class_.open(encoding=sys.getdefaultencoding(), mode="r") as file:
        # package statement must be on the first line
        first_line = file.readline()
    matches = re.search(regex, first_line)
    if matches:
        return matches.group(1)
    return ""


def _fqn(package_name: str, class_name: str) -> str:
    """Return the fully qualified name (Java style) of the class.

    Args:
        package_name: Name of the package. The default package should be an
            empty string.
        class_name: Canonical name of the class.
    Return:
        The fully qualified name of the class.
    """
    return class_name if not package_name else "{}.{}".format(package_name, class_name)


def _check_directory_corresponds_to_package(path, package):
    """Check that the path ends in a directory structure that corresponds
    to the package prefix.
    """
    required_dir_structure = package.replace(".", os.path.sep)
    if not str(path).endswith(required_dir_structure):
        msg = (
            "Directory structure does not conform to package statement. Dir:"
            " '{}' Package: '{}'".format(path, package)
        )
        raise _ActException(plug.HookResult(SECTION, Status.ERROR, msg))
