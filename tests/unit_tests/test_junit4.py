"""

.. important::

    For these tests to run, the following is required:

        1. ``javac`` must be installed.
        2. A path to ``hamcrest-core-1.3.jar`` must be in the environment
        variable REPOBEE_JUNIT4_HAMCREST.
        3. A path to ``junit-4.12.jar`` must be in the environment variable
        REPOBEE_JUNIT4_JUNIT.

"""

import pathlib
import os
from configparser import ConfigParser
from argparse import ArgumentParser
from argparse import Namespace

import pytest

import repobee_plug as plug
from repobee_junit4 import junit4
from repobee_junit4 import _junit4_runner

import envvars

CUR_DIR = pathlib.Path(__file__).parent
REPO_DIR = CUR_DIR / "repos"

MASTER_REPO_NAMES = (
    "week-10",
    "week-11",
    "week-12",
    "week-13",
    "week-14",
    "packaged-code",
    "multiple-packages",
)

# default values for CLI args
JUNIT_PATH = str(envvars.JUNIT_PATH)
HAMCREST_PATH = str(envvars.HAMCREST_PATH)

RTD = str(CUR_DIR / "reference-tests")
IGNORE_TESTS = ["FiboTest"]
CLASSPATH = "some-stuf:nice/path:path/to/unimportant/lib.jar"
VERBOSE = False
VERY_VERBOSE = False
DISABLE_SECURITY = False
RUN_STUDENT_TESTS = False
TIMEOUT = 20

CLASSPATH_WITH_JARS = CLASSPATH + ":{}:{}".format(JUNIT_PATH, HAMCREST_PATH)


@pytest.fixture
def junit4_hooks():
    return junit4.JUnit4Hooks()


def setup_args(
    master_repo_names=MASTER_REPO_NAMES,
    reference_tests_dir=RTD,
    ignore_tests=IGNORE_TESTS,
    hamcrest_path=HAMCREST_PATH,
    junit_path=JUNIT_PATH,
    verbose=VERBOSE,
    very_verbose=VERY_VERBOSE,
    disable_security=DISABLE_SECURITY,
    run_student_tests=RUN_STUDENT_TESTS,
    timeout=TIMEOUT,
):
    """Return an args namespace with the specified values."""
    return Namespace(
        master_repo_names=master_repo_names,
        junit4_reference_tests_dir=reference_tests_dir,
        junit4_ignore_tests=ignore_tests,
        junit4_junit_path=junit_path,
        junit4_hamcrest_path=hamcrest_path,
        junit4_verbose=verbose,
        junit4_very_verbose=very_verbose,
        junit4_disable_security=disable_security,
        junit4_run_student_tests=run_student_tests,
        junit4_timeout=timeout,
    )


def empty_args(
    master_repo_names=None,
    reference_tests_dir=None,
    ignore_tests=None,
    hamcrest_path=None,
    junit_path=None,
    verbose=None,
    very_verbose=None,
    disable_security=None,
    run_student_tests=None,
    timeout=None,
):
    """Return an args namespace where all args default to None."""
    return Namespace(
        master_repo_names=master_repo_names,
        junit4_reference_tests_dir=reference_tests_dir,
        junit4_ignore_tests=ignore_tests,
        junit4_junit_path=junit_path,
        junit4_hamcrest_path=hamcrest_path,
        junit4_verbose=verbose,
        junit4_very_verbose=very_verbose,
        junit4_disable_security=disable_security,
        junit4_run_student_tests=run_student_tests,
        junit4_timeout=timeout,
    )


@pytest.fixture
def full_args():
    """Return a filled Args instance."""
    return setup_args()


@pytest.fixture
def full_config_parser():
    parser = ConfigParser()
    parser[junit4.SECTION] = dict(
        hamcrest_path=HAMCREST_PATH,
        junit_path=JUNIT_PATH,
        reference_tests_dir=RTD,
        timeout=str(TIMEOUT),
    )
    return parser


@pytest.fixture(autouse=True)
def getenv_empty_classpath(mocker):
    """Classpath must be empty by default for tests to run as expected."""

    def side_effect(name):
        return None if name == "CLASSPATH" else os.getenv(name)

    getenv_mock = mocker.patch(
        "os.getenv", autospec=True, side_effect=side_effect
    )
    return getenv_mock


@pytest.fixture
def getenv_with_classpath(getenv_empty_classpath):
    side_effect = (
        lambda name: CLASSPATH if name == "CLASSPATH" else os.getenv(name)
    )
    getenv_empty_classpath.side_effect = side_effect


class TestParseArgs:
    def test_all_args(self, junit4_hooks, full_args):
        """Test that args-related attributes are correctly set when all of them
        are in the args namespace.
        """
        junit4_hooks._handle_args(full_args)

        assert junit4_hooks._master_repo_names == MASTER_REPO_NAMES
        assert junit4_hooks._reference_tests_dir == RTD
        assert junit4_hooks._ignore_tests == IGNORE_TESTS
        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH
        assert junit4_hooks._verbose == VERBOSE
        assert junit4_hooks._very_verbose == VERY_VERBOSE
        assert junit4_hooks._disable_security == DISABLE_SECURITY
        assert junit4_hooks._run_student_tests == RUN_STUDENT_TESTS
        assert junit4_hooks._timeout == TIMEOUT

    def test_defaults_are_overwritten(self, junit4_hooks, full_args):
        """Test that ignore_tests, hamcrest_path and junit_path are all
        overwritten by the parse_args method, even if they are set to something
        previously.
        """
        junit4_hooks._ignore_tests = "this isn't even a list"
        junit4_hooks._hamcrest_path = "wrong/path"
        junit4_hooks._junit_path = "also/wrong/path"
        junit4_hooks._reference_tests_dir = "some/cray/dir"
        junit4_hooks._timeout = 9999

        junit4_hooks._handle_args(full_args)

        assert junit4_hooks._ignore_tests == IGNORE_TESTS
        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH
        assert junit4_hooks._reference_tests_dir == RTD
        assert junit4_hooks._timeout == TIMEOUT

    def test_defaults_are_kept_if_not_specified_in_args(
        self, junit4_hooks, full_args
    ):
        """Test that defaults are not overwritten if they are falsy in the
        args. This does not test the timout attribute as that has a hard-coded
        default.
        """
        args = empty_args(master_repo_names=MASTER_REPO_NAMES)
        expected_ignore_tests = ["some", "tests"]
        expected_hamcrest_path = HAMCREST_PATH
        expected_junit_path = JUNIT_PATH
        expected_rtd = RTD
        expected_disable_security = False

        junit4_hooks._ignore_tests = expected_ignore_tests
        junit4_hooks._hamcrest_path = expected_hamcrest_path
        junit4_hooks._junit_path = expected_junit_path
        junit4_hooks._reference_tests_dir = expected_rtd
        junit4_hooks._disable_security = expected_disable_security

        junit4_hooks._handle_args(args)

        assert junit4_hooks._ignore_tests == expected_ignore_tests
        assert junit4_hooks._hamcrest_path == expected_hamcrest_path
        assert junit4_hooks._junit_path == expected_junit_path
        assert junit4_hooks._reference_tests_dir == expected_rtd
        assert junit4_hooks._disable_security == expected_disable_security

    def test_raises_if_argument_junit_jar_does_not_exist(self, junit4_hooks):
        """Test that the plugin raises if a JUnit jar passed as a command line
        argument does not exist.
        """
        junit_path = "/no/jar/here/" + _junit4_runner.JUNIT_JAR
        args = empty_args(junit_path=junit_path, hamcrest_path=HAMCREST_PATH)

        with pytest.raises(plug.PlugError) as exc_info:
            junit4_hooks._handle_args(args)

        assert "{} is not a file".format(junit_path) in str(exc_info.value)

    def test_raises_if_config_file_junit_jar_does_not_exist(
        self, junit4_hooks
    ):
        """Test that the plugin raises if a JUnit jar specified in the config
        file does not actually exist. That equates to a situation where the
        junit_path is already set when parsing arguments, but is not passed as
        an argument.
        """
        junit_path = "/no/jar/here/either/" + _junit4_runner.JUNIT_JAR
        junit4_hooks._junit_path = junit_path
        junit4_hooks._hamcrest_path = HAMCREST_PATH
        args = empty_args()

        with pytest.raises(plug.PlugError) as exc_info:
            junit4_hooks._handle_args(args)

        assert "{} is not a file".format(junit_path) in str(exc_info.value)

    def test_raises_if_classpath_junit_jar_does_not_exist(self, junit4_hooks):
        """Test that the plugin raises if a JUnit jar specified only on the
        CLASSPATH variable does not actually exist.
        """
        junit_path = "/no/jar/on/this/classpath/" + _junit4_runner.JUNIT_JAR
        junit4_hooks._hamcrest_path = HAMCREST_PATH
        junit4_hooks._classpath = os.pathsep.join(
            ["/garbage/path/", junit_path, HAMCREST_PATH]
        )
        args = empty_args()

        with pytest.raises(plug.PlugError) as exc_info:
            junit4_hooks._handle_args(args)

        assert "{} is not a file".format(junit_path) in str(exc_info.value)


class TestConfigHook:
    def test_with_full_config(
        self, getenv_with_classpath, junit4_hooks, full_config_parser
    ):
        junit4_hooks.config_hook(full_config_parser)

        assert junit4_hooks._hamcrest_path == HAMCREST_PATH
        assert junit4_hooks._junit_path == JUNIT_PATH
        assert junit4_hooks._classpath == CLASSPATH
        assert junit4_hooks._timeout == TIMEOUT

    def test_with_empty_config(self, getenv_with_classpath, junit4_hooks):
        expected_junit = junit4_hooks._junit_path
        expected_hamcrest = junit4_hooks._hamcrest_path

        parser = ConfigParser()

        junit4_hooks.config_hook(parser)

        assert junit4_hooks._hamcrest_path == expected_hamcrest
        assert junit4_hooks._junit_path == expected_junit
        assert junit4_hooks._classpath == CLASSPATH

    def test_raises_on_non_integer_timeout(
        self, getenv_with_classpath, junit4_hooks, full_config_parser
    ):
        val = "hello"
        full_config_parser[junit4.SECTION]["timeout"] = val

        with pytest.raises(plug.PlugError) as exc_info:
            junit4_hooks.config_hook(full_config_parser)

        assert (
            "config value timeout in section [{}] must be an integer"
            ", but was: {}"
        ).format(junit4.SECTION, val) in str(exc_info.value)


class TestCloneParserHook:
    @pytest.mark.parametrize(
        "verbose, very_verbose", [(None, None), (False, True), (True, False)]
    )
    def test_arguments_get_added(self, junit4_hooks, verbose, very_verbose):
        parser = ArgumentParser()
        sys_args = [
            "--junit4-reference-tests-dir",
            RTD,
            "--junit4-ignore-tests",
            " ".join(IGNORE_TESTS),
            "--junit4-hamcrest-path",
            HAMCREST_PATH,
            "--junit4-junit-path",
            JUNIT_PATH,
            "--junit4-timeout",
            str(TIMEOUT),
        ]

        if verbose:
            sys_args += ["--junit4-verbose"]
        if very_verbose:
            sys_args += ["--junit4-very-verbose"]

        junit4_hooks._add_option(parser)

        args = parser.parse_args(sys_args)

        assert args.junit4_reference_tests_dir == RTD
        assert args.junit4_ignore_tests == IGNORE_TESTS
        assert args.junit4_hamcrest_path == HAMCREST_PATH
        assert args.junit4_junit_path == JUNIT_PATH
        assert args.junit4_verbose == (False if verbose is None else verbose)
        assert args.junit4_very_verbose == (
            False if very_verbose is None else very_verbose
        )
        assert args.junit4_timeout == TIMEOUT

    def test_verbose_and_very_verbose_mutually_exclusive(self, junit4_hooks):
        """Test that verbose and very_verbose can't both be true at the same
        time.
        """
        parser = ArgumentParser()
        sys_args = [
            "--junit4-reference-tests-dir",
            RTD,
            "--junit4-hamcrest-path",
            HAMCREST_PATH,
            "--junit4-junit-path",
            JUNIT_PATH,
            "--junit4-verbose",
            "--junit4-very-verbose",
        ]

        junit4_hooks._add_option(parser)

        with pytest.raises(SystemExit):
            parser.parse_args(sys_args)

    @pytest.mark.parametrize("skip_arg", ["ham", "junit", "rtd"])
    def test_args_required_if_undefined(self, junit4_hooks, skip_arg):
        """Test that junit, hamcrest and rtd args are required if they are not
        defined in either config or classpath (for hamcrest and junit).
        """
        parser = ArgumentParser()
        sys_args = ["--junit4-ignore-tests", " ".join(IGNORE_TESTS)]

        if skip_arg != "ham":
            sys_args.extend(["--junit4-hamcrest-path", HAMCREST_PATH])
        if skip_arg != "junit":
            sys_args.extend(["--junit4-junit-path", JUNIT_PATH])
        if skip_arg != "rtd":
            sys_args.extend(["--junit4-refernce-tests-dir", RTD])

        junit4_hooks._add_option(parser)

        with pytest.raises(SystemExit):
            parser.parse_args(sys_args)

    def test_hamcrest_and_junit_not_required_if_on_classpath(
        self, getenv_empty_classpath
    ):
        """Just checks that there is no chrash."""
        config_parser = ConfigParser()
        arg_parser = ArgumentParser()
        sys_args = [
            "--junit4-reference-tests-dir",
            RTD,
            "--junit4-ignore-tests",
            " ".join(IGNORE_TESTS),
        ]
        getenv_empty_classpath.side_effect = (
            lambda name: CLASSPATH_WITH_JARS if name == "CLASSPATH" else None
        )

        # this is where the classpath is picked up, still setup!
        hooks = junit4.JUnit4Hooks()
        hooks.config_hook(config_parser)

        # this is the actual test
        hooks._add_option(arg_parser)
        arg_parser.parse_args(sys_args)  # should not crash!

    def test_args_not_required_if_in_config(
        self, junit4_hooks, full_config_parser
    ):
        """Test that junit, hamcrest and rtd args are not required if they are
        in the config.
        """
        junit4_hooks.config_hook(full_config_parser)
        parser = ArgumentParser()
        junit4_hooks._add_option(parser)

        parser.parse_args([])  # should not crash


def test_register():
    """Just test that there is no crash"""
    plug.manager.register(junit4)
