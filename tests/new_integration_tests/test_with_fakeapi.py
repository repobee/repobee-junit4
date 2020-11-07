import pathlib
import tempfile
import dataclasses
import shutil
import os

import pytest
import git

import repobee_testhelpers
import repobee_plug as plug

from repobee_junit4 import junit4
from repobee_junit4 import SECTION


class TestGenerateRTD:
    """Tests for the generate-rtd command."""

    def test_generate_reference_tests_directory(
        self, tmp_path_factory, platform_url
    ):
        # arrange
        workdir = tmp_path_factory.mktemp("workdir")
        rtd_path = workdir / "test-reference-tests-directory"

        # act
        run_generate_rtd(base_url=platform_url, rtd=rtd_path, workdir=workdir)

        # assert
        rtd_subdirs = list(rtd_path.iterdir())
        assert set(ASSIGNMENT_NAMES) == {subdir.name for subdir in rtd_subdirs}
        iterations = 0
        for assignment_name in ASSIGNMENT_NAMES:
            iterations += 1
            assignment_tests_dir = rtd_path / assignment_name
            test_files = {
                f.relative_to(assignment_tests_dir)
                for f in assignment_tests_dir.rglob("*")
            }
            assert test_files == EXPECTED_REFERENCE_TESTS[assignment_name]

        assert iterations > 0, "the assertion loop did not execute"

    def test_use_generated_reference_tests_directory(
        self, tmp_path_factory, platform_url, setup_student_repos
    ):
        """Test using a generated RTD with the clone command."""
        # arrange
        workdir = tmp_path_factory.mktemp("workdir")
        rtd_path = workdir / "test-reference-tests-directory"
        run_generate_rtd(base_url=platform_url, rtd=rtd_path, workdir=workdir)
        clone_dir = workdir / "clone_dir"
        clone_dir.mkdir()

        # act
        results = repobee_testhelpers.funcs.run_repobee(
            f"repos clone -a {ASSIGNMENTS_ARG} "
            f"--base-url {platform_url} "
            f"--junit4-reference-tests-dir {rtd_path} "
            f"--junit4-hamcrest-path {HAMCREST_PATH} "
            f"--junit4-junit-path {JUNIT_PATH} ",
            plugins=[junit4],
            workdir=clone_dir,
        )

        # assert
        iterations = 0
        for repo_name in plug.generate_repo_names(
            repobee_testhelpers.const.STUDENT_TEAMS, ASSIGNMENT_NAMES
        ):
            iterations += 1
            first_result, *rest = results[repo_name]
            assert not rest, "there should only be one result"
            assert first_result.name == SECTION
            assert first_result.status != plug.Status.ERROR

        assert iterations > 0, "the assertion loop did not execute"


@dataclasses.dataclass(frozen=True)
class TemplateRepoDir:
    root: pathlib.Path

    def __post_init__(self):
        assert self.master_branch.is_dir()
        assert self.solutions_branch.is_dir()

    @property
    def master_branch(self):
        return self.root / "master_branch"

    @property
    def solutions_branch(self):
        return self.root / "solutions_branch"


SOLUTIONS_BRANCH = "solutions"
TEMPLATE_REPO_DIRS = [
    TemplateRepoDir(repo_dir)
    for repo_dir in (
        pathlib.Path(__file__).parent / "template_repos"
    ).iterdir()
    if repo_dir.is_dir()
]
ASSIGNMENT_NAMES = [
    template_dir.root.name for template_dir in TEMPLATE_REPO_DIRS
]
ASSIGNMENTS_ARG = " ".join(ASSIGNMENT_NAMES)
EXPECTED_REFERENCE_TESTS = {
    repo_dir.root.name: {
        test_file.relative_to(repo_dir.solutions_branch / "src")
        for test_file in repo_dir.solutions_branch.rglob("*Test.java")
    }
    for repo_dir in TEMPLATE_REPO_DIRS
}

HAMCREST_PATH = pathlib.Path(os.getenv("REPOBEE_JUNIT4_JUNIT")).resolve(
    strict=True
)
JUNIT_PATH = pathlib.Path(os.getenv("REPOBEE_JUNIT4_HAMCREST")).resolve(
    strict=True
)


def run_generate_rtd(
    base_url: str,
    rtd: pathlib.Path,
    workdir: pathlib.Path,
    template_org_name: str = repobee_testhelpers.const.TEMPLATE_ORG_NAME,
    branch: str = SOLUTIONS_BRANCH,
    assignments: str = ASSIGNMENTS_ARG,
):
    """Helper for running the generate-rtd command."""
    return repobee_testhelpers.funcs.run_repobee(
        f"junit4 generate-rtd -a {assignments} "
        f"--base-url {base_url} "
        f"--template-org-name "
        f"{repobee_testhelpers.const.TEMPLATE_ORG_NAME} "
        f"--branch {SOLUTIONS_BRANCH} "
        f"--reference-tests-dir {rtd}",
        plugins=[junit4],
        workdir=workdir,
    )


@pytest.fixture(autouse=True)
def setup_template_repos(platform_url, platform_dir):
    for template_repo_dir in TEMPLATE_REPO_DIRS:
        template_repo_dir_in_org = (
            platform_dir
            / repobee_testhelpers.const.TEMPLATE_ORG_NAME
            / template_repo_dir.root.name
        )
        template_repo_dir_in_org.mkdir(exist_ok=False, parents=True)
        git.Repo.init(template_repo_dir_in_org, bare=True)
        template_repo_uri = f"file://{template_repo_dir_in_org.absolute()}"
        print(template_repo_uri)

        push_dir_to_branch(
            template_repo_dir.master_branch, template_repo_uri, "master"
        )
        push_dir_to_branch(
            template_repo_dir.solutions_branch,
            template_repo_uri,
            SOLUTIONS_BRANCH,
        )


@pytest.fixture
def setup_student_repos(platform_url, setup_template_repos):
    repobee_testhelpers.funcs.run_repobee(
        f"repos setup -a {ASSIGNMENTS_ARG} --base-url {platform_url}"
    )


def push_dir_to_branch(src: pathlib.Path, repo_url: str, branch: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        src_repo_path = workdir / "repo"
        shutil.copytree(src=src, dst=src_repo_path)
        repo = repobee_testhelpers.funcs.initialize_repo(src_repo_path)

        if not repo.head.ref.name == branch:
            repo.git.checkout("-b", branch)

        repo.git.push(repo_url, branch)
