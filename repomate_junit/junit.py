"""Plugin that runs javac on all files in a repo.

.. important::

    Requires ``javac`` and ``java`` to be installed, and having hamcrest and
    junit 4.12 on the CLASSPATH variable.

This plugin is mostly for demonstrational purposes, showing of a moderately
advanced external plugin.

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
from typing import Union, Iterable, Tuple

import daiquiri
from colored import bg, style

from repomate_plug import plug

LOGGER = daiquiri.getLogger(__file__)

SECTION = 'JUNIT'

HAMCREST_JAR = 'hamcrest-core-1.3.jar'
JUNIT_JAR = 'junit-4.12.jar'


def get_num_failed(test_output):
    decoded = test_output.decode(encoding=sys.getdefaultencoding())
    match = re.search(r'Failures: (\d+)', decoded)
    # TODO this is a bit unsafe, what if there is no match?
    return int(match.group(1))


@plug.Plugin
class JunitTestsHook:
    def __init__(self):
        self._master_repo_names = []
        self._reference_tests_dir = None
        self._ignore_tests = []
        self._hamcrest_path = ''
        self._junit_path = ''
        self._classpath = None

    @plug.hookimpl
    def act_on_cloned_repo(self,
                           path: Union[str, pathlib.Path]) -> plug.HookResult:
        """First run ``javac`` on all .java files in the repo to get everything
        compiled. Then run it on a test file and its corresponding production
        file.

        Assumes
        
        Args:
            path: Path to the repo.
        Returns:
            a plug.HookResult specifying the outcome.
        """
        assert self._master_repo_names
        assert self._reference_tests_dir
        path = pathlib.Path(path)
        java_files = list(path.rglob('*.java'))

        matches = list(filter(path.name.endswith, self._master_repo_names))

        if len(matches) == 1:
            master_name = matches[0]
        else:
            msg = 'no master repo name matching the student repo' \
                    if not matches else \
                    'multiple master repo names matching student repo: {}'.format(
                        ', '.join(matches))
            return plug.HookResult(SECTION, plug.ERROR, msg)

        test_dir = (self._reference_tests_dir / master_name)
        if not test_dir.exists():
            return plug.HookResult(
                SECTION, plug.ERROR,
                'no reference test directory for {} in {}'.format(
                    master_name, self._reference_tests_dir))

        test_classes = [
            file for file in test_dir.rglob('*.java')
            if file.name.endswith('Test.java')
            and file.name not in self._ignore_tests
        ]

        if not test_classes:
            return plug.HookResult(
                SECTION, plug.WARNING,
                "no files ending in `Test.java` found in {}".format(path))

        status, msg = self._javac(java_files)

        if status != plug.SUCCESS:
            return plug.HookResult(SECTION, status, msg)

        compile_succeeded, compile_failed = self._compile(
            test_classes, java_files)

        tests_succeeded, tests_failed = self._run_tests(compile_succeeded)

        msg = self._format_results(
            itertools.chain(tests_succeeded, tests_failed, compile_failed))

        status = plug.ERROR if tests_failed or compile_failed else plug.SUCCESS
        return plug.HookResult(SECTION, status, msg)

    def _format_results(self, result_pairs):
        backgrounds = {
            plug.ERROR: bg('red'),
            plug.WARNING: bg('yellow'),
            plug.SUCCESS: bg('dark_green'),
        }
        test_result_string = lambda status, msg: "{}{}:{} {}".format(backgrounds[status], status, style.RESET, msg)
        return os.linesep.join(
            [test_result_string(status, msg) for status, msg in result_pairs])

    def _compile(self, test_classes, java_files):
        failed = []
        succeeded = []
        for test_class in test_classes:
            prod_class_name = test_class.name.replace('Test.java', '.java')
            try:
                prod_class_path = list(
                    filter(lambda file: file.name == prod_class_name,
                           java_files))[0]
                adjacent_java_files = [
                    file for file in prod_class_path.parent.glob('*.java')
                    if file.name != test_class.name
                ]
                status, msg = self._javac([*adjacent_java_files, test_class])
                if status != plug.SUCCESS:
                    failed.append((status, msg))
                else:
                    succeeded.append((test_class, prod_class_path))
            except IndexError as exc:
                failed.append((plug.WARNING,
                               'no production class found for {}'.format(
                                   test_class.name)))

        return succeeded, failed

    def _run_tests(self, test_prod_class_pairs):
        succeeded = []
        failed = []
        for test_class, prod_class in test_prod_class_pairs:
            status, msg = self._junit(test_class, prod_class)
            if status != plug.SUCCESS:
                failed.append((status, msg))
            else:
                succeeded.append((status, msg))
        return succeeded, failed

    def _generate_classpath(self, test_class: pathlib.Path,
                            prod_class: pathlib.Path):
        warn = ('`{}` is not configured and not on the CLASSPATH variable.'
                'This will probably crash.')
        classpath = "{}:{!s}:{!s}".format(self._classpath, test_class.parent,
                                          prod_class.parent)
        if not (self._hamcrest_path or HAMCREST_JAR in classpath):
            LOGGER.warning(warn.format(HAMCREST_JAR))
        if not (self._junit_path or JUNIT_JAR in classpath):
            LOGGER.warning(warn.format(JUNIT_JAR))

        if self._hamcrest_path:
            classpath += ':{}'.format(self._hamcrest_path)
        if self._junit_path:
            classpath += ':{}'.format(self._junit_path)
        classpath += ':.'
        return classpath

    def _junit(self, test_class, prod_class):
        classpath = self._generate_classpath(test_class, prod_class)
        test_class_name = test_class.name[:-len(
            test_class.suffix)]  # remove .java
        command = "java -cp {} org.junit.runner.JUnitCore {}".format(
            classpath, test_class_name).split()

        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            status = plug.ERROR
            msg = "Test class {} failed {} tests".format(
                test_class_name, get_num_failed(proc.stdout))
        else:
            msg = "Test class {} passed!".format(test_class_name)
            status = plug.SUCCESS

        return status, msg

    def _javac(self, java_files: Iterable[Union[str, pathlib.Path]]
               ) -> Tuple[str, str]:
        """Run ``javac`` on all of the specified files, assuming that they are
        all ``.java`` files.

        Args:
            java_files: paths to ``.java`` files.
        Returns:
            (status, msg), where status is e.g. :py:const:`plug.ERROR` and
            the message describes the outcome in plain text.
        """
        command = 'javac {}'.format(' '.join(
            [str(f) for f in java_files])).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            status = plug.ERROR
            msg = proc.stderr.decode(sys.getdefaultencoding())
        else:
            msg = "all files compiled successfully"
            status = plug.SUCCESS

        return status, msg

    @plug.hookimpl
    def parse_args(self, args: argparse.Namespace) -> None:
        """Get command line arguments.

        Args:
            args: The full namespace returned by
            :py:func:`argparse.ArgumentParser.parse_args`
        """
        self._master_repo_names = args.master_repo_names
        self._reference_tests_dir = pathlib.Path(args.reference_tests_dir)
        self._ignore_tests = args.ignore_tests if args.ignore_tests else self._ignore_tests
        self._hamcrest_path = args.hamcrest_path if args.hamcrest_path else self._hamcrest_path
        self._junit_path = args.junit_path if args.junit_path else self._junit_path

    @plug.hookimpl
    def clone_parser_hook(self,
                          clone_parser: configparser.ConfigParser) -> None:
        """Add reference_tests_dir argument to parser.

        Args:
            clone_parser: The ``clone`` subparser.
        """
        clone_parser.add_argument(
            '-rtd',
            '--reference-tests-dir',
            help="Path to a directory with reference tests.",
            type=str,
            required=True,
        )

        clone_parser.add_argument(
            '-i',
            '--ignore-tests',
            help="Names of test classes to ignore.",
            type=str,
            nargs='+',
        )

        clone_parser.add_argument(
            '-ham',
            '--hamcrest-path',
            help="Absolute path to the `{}` library.".format(HAMCREST_JAR),
            type=str,
            # required if not picked up in config_hook nor on classpath
            required=not self._hamcrest_path
            and not HAMCREST_JAR in self._classpath,
        )

        clone_parser.add_argument(
            '-junit',
            '--junit-path',
            help="Absolute path to the `{}` library.".format(JUNIT_JAR),
            type=str,
            # required if not picked up in config_hook nor on classpath
            required=not self._junit_path and not JUNIT_JAR in self._classpath,
        )

    @plug.hookimpl
    def config_hook(self, config_parser: configparser.ConfigParser) -> None:
        """Look for hamcrest and junit paths in the config, and get the classpath.
        
        Args:
            config: the config parser after config has been read.
        """
        self._hamcrest_path = config_parser.get(
            SECTION, 'hamcrest_path', fallback=self._hamcrest_path)
        self._junit_path = config_parser.get(
            SECTION, 'junit_path', fallback=self._junit_path)
        self._classpath = os.getenv('CLASSPATH') or ''
