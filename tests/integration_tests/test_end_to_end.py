"""End-to-end tests for the plugin.

.. important::

    For these tests to run, the following is required:

        1. ``javac`` must be installed.
        2. A path to ``hamcrest-core-1.3.jar`` must be in the environment
        variable REPOBEE_JUNIT4_HAMCREST.
        3. A path to ``junit-4.12.jar`` must be in the environment variable
        REPOBEE_JUNIT4_JUNIT.
"""
import pathlib
import shutil
import tempfile
import os
import argparse
from unittest import mock
from collections import namedtuple
from functools import partial

from typing import Union

import pytest

import repobee_plug as plug
from repobee_junit4 import junit4
from repobee_junit4 import _output

import envvars

# args that are relevant for junit4
Args = namedtuple(
    "Args",
    (
        "assignments",
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

ASSIGNMENT_NAMES = (
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
NO_ASSIGNMENT_MATCH_REPO = REPO_DIR / "some-student-week-nope"
COMPILE_ERROR_REPO = REPO_DIR / "compile-error-week-10"
DIR_PATHS_WITH_SPACES = REPO_DIR / "space-week-10"
ABSTRACT_TEST_REPO = REPO_DIR / "student-week-14"
PACKAGED_CODE_REPO = REPO_DIR / "student-packaged-code"
DEFAULT_PACKAGED_CODE_REPO = REPO_DIR / "default-packaged-code"
NO_DIR_STRUCTURE_REPO = REPO_DIR / "no-dir-structure-packaged-code"
MULTIPLE_PACKAGES_REPO = REPO_DIR / "student-multiple-packages"
UNAUTHORIZED_READ_FILE_REPO = REPO_DIR / "unauthorized-read-file-week-10"
UNAUTHORIZED_NETWORK_ACCESS_REPO = (
    REPO_DIR / "unauthorized-network-access-week-10"
)
BAD_TESTS_REPO = REPO_DIR / "student-with-bad-tests-week-10"
DUPLICATE_TESTS_REPO = REPO_DIR / "student-with-duplicate-tests-week-10"
ENDLESS_WHILE_LOOP = REPO_DIR / "endless-loop-week-10"

assert SUCCESS_REPO.exists(), "test pre-requisite error, dir must exist"
assert FAIL_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TEST_DIR_REPO.exists(), "test pre-requisite error, dir must exist"
assert NO_TESTS_REPO.exists(), "test pre-requisite error, dir must exist"
assert (
    NO_ASSIGNMENT_MATCH_REPO.exists()
), "test pre-requisite error, dir must exist"
assert COMPILE_ERROR_REPO.exists(), "test pre-requisite error, dir must exist"
assert (
    DIR_PATHS_WITH_SPACES.exists()
), "test pre-reference error, dir must exit"
assert ABSTRACT_TEST_REPO.exists(), "test pre-reference error, dir must exit"

JUNIT_PATH = str(envvars.JUNIT_PATH)
HAMCREST_PATH = str(envvars.HAMCREST_PATH)

RTD = str(CUR_DIR / "reference-tests")
IGNORE_TESTS = ["FiboTest"]
CLASSPATH = "some-stuf:nice/path:path/to/unimportant/lib.jar"

CLASSPATH_WITH_JARS = CLASSPATH + ":{}:{}".format(JUNIT_PATH, HAMCREST_PATH)

NUM_PRIME_CHECKER_TESTS = 3
NUM_FIBO_TESTS = 2

DUMMY_TEAM = plug.StudentTeam(members=[], name="dummy")


def setup_hooks(
    reference_tests_dir=RTD,
    assignments=ASSIGNMENT_NAMES,
    ignore_tests=[],
    hamcrest_path=HAMCREST_PATH,
    junit_path=JUNIT_PATH,
    verbose=False,
    very_verbose=False,
    disable_security=False,
    run_student_tests=False,
    timeout=10,
):
    """Return an instance of JUnit4Hooks with pre-configured arguments."""
    hooks = junit4.JUnit4Hooks("junit4")
    hooks.args = argparse.Namespace(assignments=assignments)
    hooks.junit4_reference_tests_dir = reference_tests_dir
    hooks.junit4_ignore_tests = ignore_tests
    hooks.junit4_hamcrest_path = hamcrest_path
    hooks.junit4_junit_path = junit_path
    hooks.junit4_verbose = verbose
    hooks.junit4_very_verbose = very_verbose
    hooks.junit4_disable_security = disable_security
    hooks.junit4_run_student_tests = run_student_tests
    hooks.junit4_timeout = timeout
    return hooks


def wrap_in_student_repo(path: Union[str, pathlib.Path]) -> plug.StudentRepo:
    return plug.StudentRepo(
        name=pathlib.Path(path).name,
        team=DUMMY_TEAM,
        url="dummy_url",
        _path=pathlib.Path(path),
    )


@pytest.fixture(autouse=True)
def set_classpath(monkeypatch):
    monkeypatch.setattr("repobee_junit4.junit4.CLASSPATH", CLASSPATH)


class TestPostClone:
    """

    .. warning::

        Integration tests, slow running!
    """

    @pytest.fixture
    def default_hooks(self):
        return setup_hooks()

    def test_runs_student_tests_correctly(self):
        hooks = setup_hooks(run_student_tests=True, verbose=True)

        result = hooks.post_clone(
            wrap_in_student_repo(BAD_TESTS_REPO), api=None
        )

        assert result.status == plug.Status.WARNING
        assert "Student wrote a bad test" in str(result.msg)

    def test_handles_duplicate_student_tests(self):
        hooks = setup_hooks(run_student_tests=True, verbose=True)

        result = hooks.post_clone(
            wrap_in_student_repo(DUPLICATE_TESTS_REPO), api=None
        )

        assert result.status == plug.Status.ERROR
        assert (
            "Duplicates of the following test classes found in student "
            "repo: FiboTest.java" in str(result.msg)
        )

    def test_handles_missing_student_tests(self):
        hooks = setup_hooks(run_student_tests=True, verbose=True)

        result = hooks.post_clone(wrap_in_student_repo(SUCCESS_REPO), api=None)

        assert result.status == plug.Status.ERROR
        assert (
            "Missing the following test classes in student repo: FiboTest.java"
            in str(result.msg)
        )

    def test_converts_generic_exception_to_hook_result(self, default_hooks):
        """Test that a generic Exception raised during execution is converted
        to a hook result.
        """
        msg = "Some error message"

        def _raise_exception(*args, **kwargs):
            raise Exception(msg)

        with mock.patch(
            "repobee_junit4.junit4.JUnit4Hooks._compile_all",
            side_effect=_raise_exception,
        ):
            result = default_hooks.post_clone(
                wrap_in_student_repo(SUCCESS_REPO), api=None
            )

        assert result.status == plug.Status.ERROR
        assert result.msg == msg

    def test_with_abstract_test_class(self, default_hooks):
        """Test running the plugin when the reference tests include an abstract
        test class.
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(ABSTRACT_TEST_REPO), api=None
        )

        assert result.status == plug.Status.SUCCESS
        assert (
            _output.test_result_header(
                "PrimeCheckerTest",
                NUM_PRIME_CHECKER_TESTS,
                NUM_PRIME_CHECKER_TESTS,
                _output.SUCCESS_COLOR,
            )
            in result.msg
        )

    def test_correct_repo(self, default_hooks):
        """Test with repo that should not have test failures."""
        result = default_hooks.post_clone(
            wrap_in_student_repo(SUCCESS_REPO), api=None
        )

        assert result.status == plug.Status.SUCCESS
        assert (
            _output.test_result_header(
                "FiboTest",
                NUM_FIBO_TESTS,
                NUM_FIBO_TESTS,
                _output.SUCCESS_COLOR,
            )
            in result.msg
        )

    def test_fail_repo(self, default_hooks):
        """Test with repo that should have test failures."""
        result = default_hooks.post_clone(
            wrap_in_student_repo(FAIL_REPO), api=None
        )

        assert result.status == plug.Status.WARNING
        assert (
            _output.test_result_header(
                "PrimeCheckerTest",
                NUM_PRIME_CHECKER_TESTS,
                NUM_PRIME_CHECKER_TESTS - 2,
                _output.FAILURE_COLOR,
            )
            in result.msg
        )

    @pytest.mark.parametrize(
        "hooks",
        [setup_hooks(verbose=True), setup_hooks(very_verbose=True)],
        ids=["verbose", "very_verbose"],
    )
    def test_fail_repo_verbose(self, hooks):
        """Test verbose output on repo that fails tests."""
        expected_verbose_msg = """1) isPrimeFalseForComposites(PrimeCheckerTest)
java.lang.AssertionError: 
Expected: is <false>
     but: was <true>
2) oneIsNotPrime(PrimeCheckerTest)
java.lang.AssertionError: 
Expected: is <false>
     but: was <true>"""  # noqa: W291

        result = hooks.post_clone(wrap_in_student_repo(FAIL_REPO), api=None)

        assert (
            _output.test_result_header(
                "PrimeCheckerTest",
                NUM_PRIME_CHECKER_TESTS,
                NUM_PRIME_CHECKER_TESTS - 2,
                _output.FAILURE_COLOR,
            )
            in result.msg
        )
        assert expected_verbose_msg in result.msg

    def test_reference_test_dir_has_no_subdir_for_repo(self, default_hooks):
        """Test that a warning is returned when the reference test directory
        has no corresponding subdirectory for the specified repo.
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(NO_TEST_DIR_REPO), api=None
        )

        assert result.status == plug.Status.ERROR
        assert "no reference test directory for" in result.msg

    def test_no_tests_for_repo(self, default_hooks):
        """Test that a warning is returned when the reference test directory
        has a corresponeding subdirectory for the repo, but there are no
        test files in it.
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(NO_TESTS_REPO), api=None
        )

        assert result.status == plug.Status.WARNING
        assert "no files ending in `Test.java` found" in result.msg

    def test_error_result_when_no_assignment_match(self, default_hooks):
        """Test that the result has an error status when the student repo
        has no corresponding assignment (i.e. there is no assignment name
        contained in the student repo name).
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(NO_ASSIGNMENT_MATCH_REPO), api=None
        )

        assert result.status == plug.Status.ERROR
        assert "no assignment name matching" in result.msg

    def test_error_result_when_path_does_not_exist(self, default_hooks):
        with tempfile.TemporaryDirectory() as dirname:
            pass
        # dir is now deleted

        result = default_hooks.post_clone(
            wrap_in_student_repo(dirname), api=None
        )

        assert result.status == plug.Status.ERROR
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

            result = default_hooks.post_clone(
                wrap_in_student_repo(target), api=None
            )

        assert result.status == plug.Status.ERROR
        assert "no production class found for PrimeCheckerTest" in result.msg

    def test_error_result_on_compile_error(self, default_hooks):
        result = default_hooks.post_clone(
            wrap_in_student_repo(COMPILE_ERROR_REPO), api=None
        )

        assert result.status == plug.Status.ERROR
        assert "Compile error" in result.msg
        assert len(result.msg.split("\n")) == 1

    def test_amount_of_lines_in_compile_error_is_truncated_in_verbose_mode(
        self,
    ):
        hooks = setup_hooks(verbose=True)

        result = hooks.post_clone(
            wrap_in_student_repo(COMPILE_ERROR_REPO), api=None
        )

        assert result.status == plug.Status.ERROR
        assert len(result.msg.split(os.linesep)) == _output.DEFAULT_MAX_LINES

    def test_full_compile_error_shown_in_very_verbose_mode(self):
        hooks = setup_hooks(very_verbose=True)
        expected_error_msg_lines = """
BadClass.java:2: error: illegal start of type
    for (int i = 0; i < 10; i++, i--) {
    ^
BadClass.java:2: error: illegal start of type
    for (int i = 0; i < 10; i++, i--) {
                        ^
BadClass.java:2: error: <identifier> expected
    for (int i = 0; i < 10; i++, i--) {
                             ^
BadClass.java:2: error: <identifier> expected
    for (int i = 0; i < 10; i++, i--) {
                                  ^
4 errors
""".strip().split(
            "\n"
        )

        result = hooks.post_clone(
            wrap_in_student_repo(COMPILE_ERROR_REPO), api=None
        )

        result_lines = result.msg.strip().split("\n")
        assert result.status == plug.Status.ERROR
        # the absolute path to BadClass will differ depending on the test
        # environment so asserting the following is about as good as it gets
        assert len(result_lines) >= len(expected_error_msg_lines)

    def test_runs_correctly_when_paths_include_whitespace(self, default_hooks):
        result = default_hooks.post_clone(
            wrap_in_student_repo(DIR_PATHS_WITH_SPACES), api=None
        )

        assert result.status == plug.Status.SUCCESS

    def test_runs_with_packaged_code(self, default_hooks):
        """Test that packaged code is handled correctly."""
        result = default_hooks.post_clone(
            wrap_in_student_repo(PACKAGED_CODE_REPO), api=None
        )

        assert result.status == plug.Status.SUCCESS
        assert (
            _output.test_result_header(
                "se.repobee.fibo.FiboTest",
                NUM_FIBO_TESTS,
                NUM_FIBO_TESTS,
                _output.SUCCESS_COLOR,
            )
            in result.msg
        )

    def test_error_when_student_code_is_incorrectly_packaged(
        self, default_hooks
    ):
        """Test that a test class expecting a package errors out when the
        directory structure in the student repo does not correspond to the
        package statement in the test class.
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(NO_DIR_STRUCTURE_REPO), api=None
        )

        assert result.status == plug.Status.ERROR

    def test_runs_with_multiple_packages(self, default_hooks):
        """Test that a reference test suite with several packages is run
        correctly.
        """
        result = default_hooks.post_clone(
            wrap_in_student_repo(MULTIPLE_PACKAGES_REPO), api=None
        )

        assert result.status == plug.Status.SUCCESS

    def test_raises_when_rtd_does_not_exist(self):
        with tempfile.TemporaryDirectory() as deleted_dir:
            pass
        hooks = setup_hooks(reference_tests_dir=str(deleted_dir))

        with pytest.raises(plug.PlugError) as exc_info:
            hooks.post_clone(wrap_in_student_repo(SUCCESS_REPO), api=None)

        assert "{} is not a directory".format(str(deleted_dir)) in str(
            exc_info.value
        )

    def test_raises_when_rtd_is_a_file(self):
        """Should raise RTD exists, but is a file instead of a directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            hooks = setup_hooks(reference_tests_dir=str(tmpfile))

            with pytest.raises(plug.PlugError) as exc_info:
                hooks.post_clone(wrap_in_student_repo(SUCCESS_REPO), api=None)

        assert "{} is not a directory".format(str(tmpfile)) in str(
            exc_info.value
        )

    _CP = "{}:{}:{}:{}"

    @pytest.mark.parametrize(
        "classpath",
        [
            _CP.format(JUNIT_PATH, HAMCREST_PATH, "garbage/path", "."),
            _CP.format(HAMCREST_PATH, "garbage/path", JUNIT_PATH, "."),
            _CP.format("garbage/path", HAMCREST_PATH, ".", JUNIT_PATH),
        ],
    )
    def test_jars_found_on_classpath(self, classpath, monkeypatch):
        """Test that acting on a repo when the hamcrest and junit jars are only
        specified on the classpath works as intended.
        """
        monkeypatch.setattr("repobee_junit4.junit4.CLASSPATH", classpath)
        hooks = setup_hooks(hamcrest_path="", junit_path="")

        result = hooks.post_clone(wrap_in_student_repo(SUCCESS_REPO), api=None)

        assert result.status == plug.Status.SUCCESS

    def test_verbose_output_is_truncated(self, monkeypatch):
        """Test that long lines are truncated when running --verbose."""
        hooks = setup_hooks(verbose=True)
        line_length = 20
        monkeypatch.setattr(
            "repobee_junit4._output._truncate_lines",
            partial(_output._truncate_lines, max_len=line_length),
        )

        result = hooks.post_clone(wrap_in_student_repo(FAIL_REPO), api=None)

        lines = result.msg.split(os.linesep)[1:]  # skip summary line
        assert len(lines) > 1
        # the first line can be somewhat longer due to staus message
        # and color codes
        assert all([len(line) <= line_length for line in lines[1:]])

    def test_very_verbose_output_not_truncated(self, monkeypatch):
        """Test that long lines are not truncated when running with
        --very-verbose.
        """
        hooks = setup_hooks(very_verbose=True)
        line_length = 20
        monkeypatch.setattr(
            "repobee_junit4._output._truncate_lines",
            partial(_output._truncate_lines, max_len=line_length),
        )

        result = hooks.post_clone(wrap_in_student_repo(FAIL_REPO), api=None)

        lines = result.msg.split(os.linesep)
        assert len(lines) > 1
        # the first line can be somewhat longer due to staus message
        # and color codes
        assert any([len(line) > line_length for line in lines[1:]])

    def test_endless_loop_in_production_code_times_out(self):
        timeout = 1
        hooks = setup_hooks(timeout=timeout)

        result = hooks.post_clone(
            wrap_in_student_repo(ENDLESS_WHILE_LOOP), api=None
        )

        assert result.status == plug.Status.WARNING
        assert "Timed out after {} seconds".format(timeout) in result.msg


class TestSecurityPolicy:
    """Tests that assert that the default security policy model blocks access
    to unauthorized resources.
    """

    def test_error_on_unauthorized_read(self):
        """Test that the default security policy blocks read access to
        files.
        """
        hooks = setup_hooks(verbose=True)

        result = hooks.post_clone(
            wrap_in_student_repo(UNAUTHORIZED_READ_FILE_REPO), api=None
        )

        assert result.status == plug.Status.WARNING
        assert (
            "java.security.AccessControlException: access denied" in result.msg
        )

    def test_error_on_unauthorized_network_access(self):
        """Test that the default security policy blocks network access."""
        hooks = setup_hooks(verbose=True)

        result = hooks.post_clone(
            wrap_in_student_repo(UNAUTHORIZED_NETWORK_ACCESS_REPO), api=None
        )

        assert result.status == plug.Status.WARNING
        assert (
            "java.security.AccessControlException: access denied" in result.msg
        )

    def test_file_access_allowed_with_disabled_security(self):
        """Test that student code can access files without crashing if security
        is disabled.
        """
        hooks = setup_hooks(disable_security=True)

        result = hooks.post_clone(
            wrap_in_student_repo(UNAUTHORIZED_READ_FILE_REPO), api=None
        )

        assert result.status == plug.Status.SUCCESS
        assert (
            _output.test_result_header(
                "FiboTest",
                NUM_FIBO_TESTS,
                NUM_FIBO_TESTS,
                _output.SUCCESS_COLOR,
            )
            in result.msg
        )
