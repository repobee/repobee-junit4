import pathlib
import tempfile
import dataclasses
import git
import shutil

import pytest
import repobee_testhelpers

from repobee_junit4 import junit4


def test_with_solutions_branch_when_no_student_is_finished(
    platform_url, tmp_path_factory
):
    workdir = tmp_path_factory.mktemp("workdir")
    repobee_testhelpers.funcs.run_repobee(
        f"repos clone -a {ASSIGNMENTS_ARG} "
        f"--base-url {platform_url} "
        f"--junit4-template-org-name "
        f"{repobee_testhelpers.const.TEMPLATE_ORG_NAME} "
        f"--junit4-solutions-branch solutions ",
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
            template_repo_dir.solutions_branch, template_repo_uri, "solutions"
        )


@pytest.fixture(autouse=True)
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
