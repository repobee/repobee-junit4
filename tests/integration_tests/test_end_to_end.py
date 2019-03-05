"""End-to-end tests for the plugin.

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

import pytest

from repomate_plug import Status
from repomate_junit4 import junit4

import envvars

# args that are relevant for junit4
Args = namedtuple(
    "Args",
    (
        "master_repo_names",
        "reference_tests_dir",
        "ignore_tests",
        "hamcrest_path",
        "junit_path",
        "verbose",
        "disable_security",
    ),
)
Args.__new__.__defaults__ = (None,) * len(Args._fields)

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

SUCCESS_REPO = REPO_DIR / "some-student-week-10"
FAIL_REPO = REPO_DIR / "other-student-week-11"
NO_TEST_DIR_REPO = REPO_DIR / "some-student-week-12"
NO_TESTS_REPO = REPO_DIR / "best-student-week-13"
NO_MASTER_MATCH_REPO = REPO_DIR / "some-student-week-nope"
COMPILE_ERROR_REPO = REPO_DIR / "compile-error-week-10"
DIR_PATHS_WITH_SPACES = REPO_DIR / "space-week-10"
ABSTRACT_TEST_REPO = REPO_DIR / "student-week-14"
PACKAGED_CODE_REPO = REPO_DIR / "student-packaged-code"
DEFAULT_PACKAGED_CODE_REPO = REPO_DIR / "default-packaged-code"
NO_DIR_STRUCTURE_REPO = REPO_DIR / "no-dir-structure-packaged-code"
MULTIPLE_PACKAGES_REPO = REPO_DIR / "student-multiple-packages"
UNAUTHORIZED_READ_FILE_REPO = REPO_DIR / "unauthorized-read-file-week-10"
UNAUTHORIZED_NETWORK_ACCESS_REPO = REPO_DIR / "unauthorized-network-access-week-10"

assert SUCCESS_REPO.exists(), "test pre-requisite error, dir must exist"
assert FAIL_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TEST_DIR_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TESTS_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_MASTER_MATCH_REPO.exists(), "test pre-requisite error, dir must exist"
assert COMPILE_ERROR_REPO.exists(), "test pre-requisite error, dir must exist"
assert DIR_PATHS_WITH_SPACES.exists(), "test pre-reference error, dir must exit"
assert ABSTRACT_TEST_REPO.exists(), "test pre-reference error, dir must exit"

JUNIT_PATH = str(envvars.JUNIT_PATH)
HAMCREST_PATH = str(envvars.HAMCREST_PATH)

RTD = str(CUR_DIR / "reference-tests")
IGNORE_TESTS = ["FiboTest"]
CLASSPATH = "some-stuf:nice/path:path/to/unimportant/lib.jar"

CLASSPATH_WITH_JARS = CLASSPATH + ":{}:{}".format(JUNIT_PATH, HAMCREST_PATH)


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
        disable_security=False,
    )


@pytest.fixture
def full_config_parser():
    parser = ConfigParser()
    parser[junit4.SECTION] = dict(
        hamcrest_path=HAMCREST_PATH, junit_path=JUNIT_PATH, reference_tests_dir=RTD
    )
    return parser


@pytest.fixture(autouse=True)
def getenv_empty_classpath(mocker):
    """Classpath must be empty by default for tests to run as expected."""
    side_effect = lambda name: None if name == "CLASSPATH" else os.getenv(name)
    getenv_mock = mocker.patch("os.getenv", autospec=True, side_effect=side_effect)
    return getenv_mock


@pytest.fixture
def getenv_with_classpath(getenv_empty_classpath):
    side_effect = lambda name: CLASSPATH if name == "CLASSPATH" else os.getenv(name)
    getenv_empty_classpath.side_effect = side_effect


def setup_hooks(
    reference_tests_dir=RTD,
    master_repo_names=MASTER_REPO_NAMES,
    ignore_tests=[],
    classpath=CLASSPATH,
    hamcrest_path=HAMCREST_PATH,
    junit_path=JUNIT_PATH,
    verbose=False,
    disable_security=False,
):
    """Return an instance of JUnit4Hooks with pre-configured arguments."""
    hooks = junit4.JUnit4Hooks()
    hooks._reference_tests_dir = reference_tests_dir
    hooks._master_repo_names = master_repo_names
    hooks._ignore_tests = ignore_tests
    hooks._classpath = classpath
    hooks._hamcrest_path = hamcrest_path
    hooks._junit_path = junit_path
    hooks._verbose = verbose
    hooks._disable_security = disable_security
    return hooks


class TestActOnClonedRepo:
    """

    .. warning::

        Integration tests, slow running!
    """

    @pytest.fixture
    def default_hooks(self):
        return setup_hooks()

    def test_with_abstract_test_class(self, default_hooks):
        """Test running the plugin when the reference tests include an abstract test class."""
        result = default_hooks.act_on_cloned_repo(ABSTRACT_TEST_REPO)

        assert result.status == Status.SUCCESS
        assert "Test class PrimeCheckerTest passed!" in result.msg

    def test_correct_repo(self, default_hooks):
        """Test with repo that should not have test failures."""
        result = default_hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.SUCCESS
        assert "Test class FiboTest passed!" in result.msg

    def test_fail_repo(self, default_hooks):
        """Test with repo that should have test failures."""
        result = default_hooks.act_on_cloned_repo(FAIL_REPO)

        assert result.status == Status.ERROR
        assert "Test class PrimeCheckerTest failed 2 tests" in result.msg

    def test_fail_repo_verbose(self):
        """Test verbose output on repo that fails tests."""
        hooks = setup_hooks(verbose=True)

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

        hooks = setup_hooks(reference_tests_dir=dirname)

        result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory" in result.msg

    def test_reference_test_dir_is_file(self):
        """Test with path to reference_tests_dir leading ot a file."""
        with tempfile.NamedTemporaryFile() as file:
            hooks = setup_hooks(reference_tests_dir=file.name)
            result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory" in result.msg

    def test_reference_test_dir_has_no_subdir_for_repo(self, default_hooks):
        """Test that a warning is returned when the reference test directory
        has no corresponding subdirectory for the specified repo.
        """
        result = default_hooks.act_on_cloned_repo(NO_TEST_DIR_REPO)

        assert result.status == Status.ERROR
        assert "no reference test directory for" in result.msg

    def test_no_tests_for_repo(self, default_hooks):
        """Test that a warning is returned when the reference test directory
        has a corresponeding subdirectory for the repo, but there are no
        test files in it.
        """
        result = default_hooks.act_on_cloned_repo(NO_TESTS_REPO)

        assert result.status == Status.WARNING
        assert "no files ending in `Test.java` found" in result.msg

    def test_error_result_when_no_master_repo_match(self, default_hooks):
        """Test that the result has an error status when the student repo
        has no corresponding master repo (i.e. there is no master repo name
        contained in the student repo name).
        """
        result = default_hooks.act_on_cloned_repo(NO_MASTER_MATCH_REPO)

        assert result.status == Status.ERROR
        assert "no master repo name matching" in result.msg

    def test_error_result_when_path_does_not_exist(self, default_hooks):
        with tempfile.TemporaryDirectory() as dirname:
            pass
        # dir is now deleted

        result = default_hooks.act_on_cloned_repo(dirname)

        assert result.status == Status.ERROR
        assert "student repo {} does not exist".format(dirname) in result.msg

    def test_error_result_when_prod_class_missing(self, default_hooks):
        """Test that the result has an error status if the student repo does
        not have a production class for one or more test classes.
        """
        # use week-10 repo with week-11 name
        with tempfile.TemporaryDirectory() as tmpdir:
            assert SUCCESS_REPO.name.endswith(
                "week-10"
            ), "meta assert, test incorrect if fail"
            target = str(pathlib.Path(tmpdir) / "student-week-11")
            shutil.copytree(str(SUCCESS_REPO), target)

            result = default_hooks.act_on_cloned_repo(target)

        assert result.status == Status.ERROR
        assert "no production class found for PrimeCheckerTest" in result.msg

    def test_error_result_on_compile_error(self, default_hooks):
        result = default_hooks.act_on_cloned_repo(str(COMPILE_ERROR_REPO))

        assert result.status == Status.ERROR
        assert "error: illegal start of type" in result.msg

    def test_runs_correctly_when_paths_include_whitespace(self, default_hooks):
        result = default_hooks.act_on_cloned_repo(DIR_PATHS_WITH_SPACES)

        assert result.status == Status.SUCCESS

    def test_runs_with_packaged_code(self, default_hooks):
        """Test that packaged code is handled correctly."""
        result = default_hooks.act_on_cloned_repo(PACKAGED_CODE_REPO)

        assert result.status == Status.SUCCESS
        assert "Test class se.repomate.fibo.FiboTest passed!" in str(result.msg)

    def test_error_when_student_code_is_incorrectly_packaged(self, default_hooks):
        """Test that a test class expecting a package errors out when the
        directory structure in the student repo does not correspond to the
        package statement in the test class.
        """
        result = default_hooks.act_on_cloned_repo(NO_DIR_STRUCTURE_REPO)

        assert result.status == Status.ERROR

    def test_runs_with_multiple_packages(self, default_hooks):
        """Test that a reference test suite with several packages is run
        correctly.
        """
        result = default_hooks.act_on_cloned_repo(MULTIPLE_PACKAGES_REPO)

        assert result.status == Status.SUCCESS

    _CP = "{}:{}:{}:{}"

    @pytest.mark.parametrize(
        "classpath",
        [
            _CP.format(JUNIT_PATH, HAMCREST_PATH, "garbage/path", "."),
            _CP.format(HAMCREST_PATH, "garbage/path", JUNIT_PATH, "."),
            _CP.format("garbage/path", HAMCREST_PATH, ".", JUNIT_PATH),
        ],
    )
    def test_jars_found_on_classpath(self, classpath):
        """Test that acting on a repo when the hamcrest and junit jars are only
        specified on the classpath works as intended.
        """
        hooks = setup_hooks(hamcrest_path="", junit_path="", classpath=classpath)

        result = hooks.act_on_cloned_repo(SUCCESS_REPO)

        assert result.status == Status.SUCCESS


class TestSecurityPolicy:
    """Tests that assert that the default security policy model blocks access
    to unauthorized resources.
    """

    def test_error_on_unauthorized_read(self):
        """Test that the default security policy blocks read access to
        files.
        """
        hooks = setup_hooks(verbose=True)

        result = hooks.act_on_cloned_repo(UNAUTHORIZED_READ_FILE_REPO)

        assert result.status == Status.ERROR
        assert "java.security.AccessControlException: access denied" in result.msg

    def test_error_on_unauthorized_network_access(self):
        """Test that the default security policy blocks network access."""
        hooks = setup_hooks(verbose=True)

        result = hooks.act_on_cloned_repo(UNAUTHORIZED_NETWORK_ACCESS_REPO)

        assert result.status == Status.ERROR
        assert "java.security.AccessControlException: access denied" in result.msg

    def test_file_access_allowed_with_disabled_security(self):
        """Test that student code can access files without crashing if security
        is disabled.
        """
        hooks = setup_hooks(disable_security=True)

        result = hooks.act_on_cloned_repo(UNAUTHORIZED_READ_FILE_REPO)

        assert result.status == Status.SUCCESS
        assert "Test class FiboTest passed!" in result.msg
