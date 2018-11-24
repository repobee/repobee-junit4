"""

.. important::

    For these tests to run, the following is required:

        1. ``javac`` must be installed.
        2. A path to ``hamcrest-core-1.3.jar`` must be in the environment
        variable REPOMATE_JUNIT4_HAMCREST.
        3. A path to ``junit-4.12.jar`` must be in the environment variable
        REPOMATE_JUNIT4_JUNIT.

"""

import pathlib
import shutil
import tempfile
import os
from configparser import ConfigParser
from collections import namedtuple
from argparse import ArgumentParser

import pytest

import repomate_plug as plug
from repomate_plug import Status
from repomate_junit4 import junit4

# args that are relevant for junit4
Args = namedtuple('Args',
                  ('master_repo_names', 'reference_tests_dir', 'ignore_tests',
                   'hamcrest_path', 'junit_path', 'verbose'))
Args.__new__.__defaults__ = (None, ) * len(Args._fields)

CUR_DIR = pathlib.Path(__file__).parent
REPO_DIR = CUR_DIR / 'repos'

MASTER_REPO_NAMES = ('week-10', 'week-11', 'week-12', 'week-13')

SUCCESS_REPO = REPO_DIR / 'some-student-week-10'
FAIL_REPO = REPO_DIR / 'other-student-week-11'
NO_TEST_DIR_REPO = REPO_DIR / 'some-student-week-12'
NO_TESTS_REPO = REPO_DIR / 'best-student-week-13'
NO_MASTER_MATCH_REPO = REPO_DIR / 'some-student-week-nope'
COMPILE_ERROR_REPO = REPO_DIR / 'compile-error-week-10'
DIR_PATHS_WITH_SPACES = REPO_DIR / 'space-week-10'

assert SUCCESS_REPO.exists(), "test pre-requisite error, dir must exist"
assert FAIL_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TEST_DIR_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TESTS_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_MASTER_MATCH_REPO.exists(
), "test pre-requisite error, dir must exist"
assert COMPILE_ERROR_REPO.exists(), "test pre-requisite error, dir must exist"
assert DIR_PATHS_WITH_SPACES.exists(
), "test pre-reference error, dir must exit"

RTD = str(CUR_DIR / 'reference-tests')
JUNIT_PATH = str(pytest.constants.JUNIT_PATH)
HAMCREST_PATH = str(pytest.constants.HAMCREST_PATH)
IGNORE_TESTS = ['FiboTest']
CLASSPATH = 'some-stuf:nice/path:path/to/unimportant/lib.jar'

CLASSPATH_WITH_JARS = CLASSPATH + ':{}:{}'.format(JUNIT_PATH, HAMCREST_PATH)


@pytest.fixture
def junit4_hooks():
    return junit4.JUnit4Hooks()


@pytest.fixture
def full_args():
    """Return a filled Args instance."""
    return Args(
        master_repo_names=MASTER_REPO_NAMES,
        reference_tests_dir=RTD,
        ignore_tests=IGNORE_TESTS,
        hamcrest_path=HAMCREST_PATH,
        junit_path=JUNIT_PATH,
        verbose=False,
    )


@pytest.fixture
def full_config_parser():
    parser = ConfigParser()
    parser[junit4.SECTION] = dict(
        hamcrest_path=HAMCREST_PATH,
        junit_path=JUNIT_PATH,
        reference_tests_dir=RTD)
    return parser


@pytest.fixture(autouse=True)
def getenv_empty_classpath(mocker):
    """Classpath must be empty by default for tests to run as expected."""
    side_effect = lambda name: None if name == 'CLASSPATH' else os.getenv(name)
    getenv_mock = mocker.patch(
        'os.getenv', autospec=True, side_effect=side_effect)
    return getenv_mock


@pytest.fixture
def getenv_with_classpath(getenv_empty_classpath):
    side_effect = lambda name: CLASSPATH if name == 'CLASSPATH' else os.getenv(name)
    getenv_empty_classpath.side_effect = side_effect


class TestActOnClonedRepo:
    """

    .. warning::

        These tests run slow!

    """

    def setup_hooks(self,
                    *,
                    reference_tests_dir=RTD,
                    master_repo_names=MASTER_REPO_NAMES,
                    ignore_tests=[],
                    classpath=CLASSPATH,
                    hamcrest_path=HAMCREST_PATH,
                    junit_path=JUNIT_PATH,
                    verbose=False):
        hooks = junit4.JUnit4Hooks()
        hooks._reference_tests_dir = reference_tests_dir
        hooks._master_repo_names = master_repo_names
        hooks._ignore_tests = ignore_tests
        hooks._classpath = classpath
        hooks._hamcrest_path = hamcrest_path
        hooks._junit_path = junit_path
        hooks._verbose = verbose
        return hooks

    @pytest.fixture
    def hooks(self):
        return self.setup_hooks()

    def test_correct_repo(self, hooks):
        """Test with repo that should not have test failures."""
        result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.SUCCESS
        assert "Test class FiboTest passed!" in result.msg

    def test_fail_repo(self, hooks):
        """Test with repo that should have test failures."""
        result = hooks.act_on_cloned_repo(FAIL_REPO)

        assert result.status == Status.ERROR
        assert "Test class PrimeCheckerTest failed 2 tests" in result.msg

    def test_fail_repo_verbose(self):
        """Test verbose output on repo that fails tests."""
        hooks = self.setup_hooks(verbose=True)

        expected_verbose_msg = """1) isPrimeFalseForComposites(PrimeCheckerTest)
java.lang.AssertionError: 
Expected: is <false>
     but: was <true>
2) oneIsNotPrime(PrimeCheckerTest)
java.lang.AssertionError: 
Expected: is <false>
     but: was <true>"""

        result = hooks.act_on_cloned_repo(FAIL_REPO)

        assert "Test class PrimeCheckerTest failed 2 tests" in result.msg
        assert expected_verbose_msg in result.msg

    def test_no_reference_tests_dir(self):
        """Test with invalid path to reference_tests_dir."""
        with tempfile.TemporaryDirectory() as d:
            dirname = d
        # dir is now deleted

        hooks = self.setup_hooks(reference_tests_dir=dirname)

        result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory" in result.msg

    def test_reference_test_dir_is_file(self):
        """Test with path to reference_tests_dir leading ot a file."""
        with tempfile.NamedTemporaryFile() as file:
            hooks = self.setup_hooks(reference_tests_dir=file.name)
            result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory" in result.msg

    def test_reference_test_dir_has_no_subdir_for_repo(self, hooks):
        """Test that a warning is returned when the reference test directory
        has no corresponding subdirectory for the specified repo.
        """
        result = hooks.act_on_cloned_repo(NO_TEST_DIR_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory for" in result.msg

    def test_no_tests_for_repo(self, hooks):
        """Test that a warning is returned when the reference test directory
        has a corresponeding subdirectory for the repo, but there are no
        test files in it.
        """
        result = hooks.act_on_cloned_repo(NO_TESTS_REPO)

        assert result.status == Status.WARNING
        assert "no files ending in `Test.java` found" in result.msg

    def test_error_result_when_no_master_repo_match(self, hooks):
        """Test that the result has an error status when the student repo
        has no corresponding master repo (i.e. there is no master repo name
        contained in the student repo name).
        """
        result = hooks.act_on_cloned_repo(NO_MASTER_MATCH_REPO)

        assert result.status == Status.ERROR
        assert "no master repo name matching" in result.msg

    def test_error_result_when_path_does_not_exist(self, hooks):
        with tempfile.TemporaryDirectory() as dirname:
            pass
        # dir is now deleted

        result = hooks.act_on_cloned_repo(dirname)

        assert result.status == Status.ERROR
        assert "student repo {} does not exist".format(dirname) in result.msg

    def test_error_result_when_prod_class_missing(self, hooks):
        """Test that the result has an error status if the student repo does
        not have a production class for one or more test classes.
        """
        # use week-10 repo with week-11 name
        with tempfile.TemporaryDirectory() as tmpdir:
            assert SUCCESS_REPO.name.endswith(
                'week-10'), "meta assert, test incorrect if fail"
            target = str(pathlib.Path(tmpdir) / 'student-week-11')
            shutil.copytree(str(SUCCESS_REPO), target)

            result = hooks.act_on_cloned_repo(target)

        assert result.status == Status.ERROR
        assert 'no production class found for PrimeCheckerTest' in result.msg

    def test_error_result_on_compile_error(self, hooks):
        result = hooks.act_on_cloned_repo(str(COMPILE_ERROR_REPO))

        assert result.status == Status.ERROR
        assert 'error: illegal start of type' in result.msg

    def test_runs_correctly_when_paths_include_whitespace(self, hooks):
        result = hooks.act_on_cloned_repo(DIR_PATHS_WITH_SPACES)

        assert result.status == Status.SUCCESS


class TestParseArgs:
    def test_all_args(self, junit4_hooks, full_args):
        """Test that args-related attributes are correctly set when all of them
        are in the args namespace.
        """
        junit4_hooks.parse_args(full_args)

        assert junit4_hooks._master_repo_names == MASTER_REPO_NAMES
        assert junit4_hooks._reference_tests_dir == RTD
        assert junit4_hooks._ignore_tests == IGNORE_TESTS
        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH

    def test_defaults_are_overwritten(self, junit4_hooks, full_args):
        """Test that ignore_tests, hamcrest_path and junit_path are all
        overwritten by the parse_args method, even if they are set to something
        previously.
        """
        junit4_hooks._ignore_tests = "this isn't even a list"
        junit4_hooks._hamcrest_path = 'wrong/path'
        junit4_hooks._junit_path = 'also/wrong/path'
        junit4_hooks._reference_tests_dir = 'some/cray/dir'

        junit4_hooks.parse_args(full_args)

        assert junit4_hooks._ignore_tests == IGNORE_TESTS
        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH
        assert junit4_hooks._reference_tests_dir == RTD

    def test_defaults_are_kept_if_not_specified_in_args(
            self, junit4_hooks, full_args):
        """Test that defaults are not overwritten if they are falsy in the
        args.
        """
        args = Args(master_repo_names=MASTER_REPO_NAMES)
        expected_ignore_tests = ['some', 'tests']
        expected_hamcrest_path = 'some/path/to/{}'.format(junit4.HAMCREST_JAR)
        expected_junit_path = 'other/path/to/{}'.format(junit4.JUNIT_JAR)
        expected_rtd = RTD

        junit4_hooks._ignore_tests = expected_ignore_tests
        junit4_hooks._hamcrest_path = expected_hamcrest_path
        junit4_hooks._junit_path = expected_junit_path
        junit4_hooks._reference_tests_dir = expected_rtd

        junit4_hooks.parse_args(args)

        assert junit4_hooks._ignore_tests == expected_ignore_tests
        assert junit4_hooks._hamcrest_path == expected_hamcrest_path
        assert junit4_hooks._junit_path == expected_junit_path
        assert junit4_hooks._reference_tests_dir == expected_rtd


class TestConfigHook:
    def test_with_full_config(self, junit4_hooks, getenv_with_classpath,
                              full_config_parser):
        junit4_hooks.config_hook(full_config_parser)

        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH
        assert junit4_hooks._classpath == CLASSPATH

    def test_with_empty_config(self, junit4_hooks, getenv_with_classpath):
        expected_junit = junit4_hooks._junit_path
        expected_hamcrest = junit4_hooks._hamcrest_path

        parser = ConfigParser()

        junit4_hooks.config_hook(parser)

        assert junit4_hooks._hamcrest_path == expected_hamcrest
        assert junit4_hooks._junit_path == expected_junit
        assert junit4_hooks._classpath == CLASSPATH


class TestCloneParserHook:
    @pytest.mark.parametrize('verbose', (None, False, True))
    def test_arguments_get_added(self, junit4_hooks, verbose):
        """Just test that `-rtd`, `-i`, `-ham` and `-junit` get added
        correctly and that the args can then be parsed as expected.
        """
        parser = ArgumentParser()
        sys_args = [
            '-rtd', RTD, '-i', ' '.join(IGNORE_TESTS), '-ham', HAMCREST_PATH,
            '-junit', JUNIT_PATH
        ]

        if verbose:
            sys_args += ['-v']

        junit4_hooks.clone_parser_hook(parser)

        args = parser.parse_args(sys_args)

        assert args.reference_tests_dir == RTD
        assert args.ignore_tests == IGNORE_TESTS
        assert args.hamcrest_path == HAMCREST_PATH
        assert args.junit_path == JUNIT_PATH
        assert args.verbose == (False if verbose is None else verbose)

    @pytest.mark.parametrize('skip_arg', ['ham', 'junit', 'rtd'])
    def test_args_required_if_undefined(self, junit4_hooks, skip_arg):
        """Test that junit, hamcrest and rtd args are required if they are not
        defined in either config or classpath (for hamcrest and junit).
        """
        parser = ArgumentParser()
        sys_args = ['-i', ' '.join(IGNORE_TESTS)]

        if skip_arg != 'ham':
            sys_args.extend(['-ham', HAMCREST_PATH])
        if skip_arg != 'junit':
            sys_args.extend(['-junit', JUNIT_PATH])
        if skip_arg != 'rtd':
            sys_args.extend(['-rtd', RTD])

        junit4_hooks.clone_parser_hook(parser)

        with pytest.raises(SystemExit):
            parser.parse_args(sys_args)

    def test_hamcrest_and_junit_not_required_if_on_classpath(
            self, junit4_hooks, getenv_empty_classpath):
        """Just checks that there is no chrash."""
        config_parser = ConfigParser()
        arg_parser = ArgumentParser()
        sys_args = ['-rtd', RTD, '-i', ' '.join(IGNORE_TESTS)]
        getenv_empty_classpath.side_effect = \
            lambda name: CLASSPATH_WITH_JARS if name == 'CLASSPATH' else None

        # this is where the classpath is picked up, still setup!
        junit4_hooks.config_hook(config_parser)

        # this is the actual test
        junit4_hooks.clone_parser_hook(arg_parser)
        arg_parser.parse_args(sys_args)  # should not crash!

    def test_args_not_required_if_in_config(self, junit4_hooks,
                                            full_config_parser):
        """Test that junit, hamcrest and rtd args are not required if they are
        in the config.
        """
        args = Args(master_repo_names=MASTER_REPO_NAMES)
        junit4_hooks.config_hook(full_config_parser)
        parser = ArgumentParser()
        junit4_hooks.clone_parser_hook(parser)

        parser.parse_args([])  # should not crash


def test_register():
    """Just test that there is no crash"""
    plug.manager.register(junit4)
