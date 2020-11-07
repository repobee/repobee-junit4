import pathlib
import tempfile
import dataclasses
import git
import shutil

import pytest
import repobee_testhelpers

from repobee_junit4 import junit4


class TestGenerateRTD:
    """Tests for the generate-rtd command."""

    def test_generate_reference_tests_directory(
        self, tmp_path_factory, platform_url
    ):
        workdir = tmp_path_factory.mktemp("workdir")
        rtd_path = workdir / "test-reference-tests-directory"

        repobee_testhelpers.funcs.run_repobee(
            f"junit4 generate-rtd -a {ASSIGNMENTS_ARG} "
            f"--base-url {platform_url} "
            f"--template-org-name "
            f"{repobee_testhelpers.const.TEMPLATE_ORG_NAME} "
            f"--branch {SOLUTIONS_BRANCH} "
            f"--reference-tests-dir {rtd_path}",
            plugins=[junit4],
            workdir=workdir,
        )

        rtd_subdirs = list(rtd_path.iterdir())

        assert set(ASSIGNMENT_NAMES) == {subdir.name for subdir in rtd_subdirs}
        for assignment_name in ASSIGNMENT_NAMES:
            assignment_tests_dir = rtd_path / assignment_name
            test_files = {
                f.relative_to(assignment_tests_dir)
                for f in assignment_tests_dir.rglob("*")
            }
            assert test_files == EXPECTED_REFERENCE_TESTS[assignment_name]

    def test_use_generated_reference_tests_directory(
        self, tmp_path_factory, platform_url, setup_student_repos
    ):
        workdir = tmp_path_factory.mktemp("workdir")
        rtd_path = workdir / "test-reference-tests-directory"

        repobee_testhelpers.funcs.run_repobee(
            f"junit4 generate-rtd -a {ASSIGNMENTS_ARG} "
            f"--base-url {platform_url} "
            f"--template-org-name "
            f"{repobee_testhelpers.const.TEMPLATE_ORG_NAME} "
            f"--branch {SOLUTIONS_BRANCH} "
            f"--reference-tests-dir {rtd_path}",
            plugins=[junit4],
            workdir=workdir,
        )

        repobee_testhelpers.funcs.run_repobee(
            f"repos clone -a {ASSIGNMENTS_ARG} "
            f"--base-url {platform_url} "
            f"--junit4-reference-tests-dir {rtd_path} ",
            plugins=[junit4],
            workdir=workdir,
        )


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
