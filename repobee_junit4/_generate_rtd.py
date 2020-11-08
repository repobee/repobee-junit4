"""Command for generating the reference tests directory from solutions branches
in template repositories.
"""
import shutil
import pathlib
import tempfile
from typing import List

import git

import repobee_plug as plug

JUNIT4_COMMAND_CATEGORY = plug.cli.category(
    name="junit4",
    action_names=["generate-rtd"],
    help="help commands for the junit4 plugin",
)

_COMMAND_DESCRIPTION = """
Generate the reference tests directory (RTD) from template repositories by
extracting any Java test classes from the template. For each assignment
specified, a subdirectory in the reference tests directory (RTD) is created
with the name of the assignment. When generating the test directory for a given
assignment X, there must not be an X directory already in the RTD. If you want
to refresh the tests for an assignment X, then delete its corresponding
subdirectory before running this command. WARNING: This command is in alpha and
behavior may change in coming updates.
""".replace(
    "\n", " "
).strip()


class GenerateRTD(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        action=JUNIT4_COMMAND_CATEGORY.generate_rtd,
        help="generate the reference tests directory by extracting test "
        "classes from template repositories (note: alpha test)",
        description=_COMMAND_DESCRIPTION,
        base_parsers=[
            plug.cli.BaseParser.ASSIGNMENTS,
            plug.cli.BaseParser.TEMPLATE_ORG,
        ],
    )

    reference_tests_dir = plug.cli.option(
        help="path to place the root reference tets directory at",
        converter=pathlib.Path,
        required=True,
    )
    branch = plug.cli.option(
        help="the branch to search for reference tests in each template "
        "repository",
        required=True,
    )

    def command(self, api: plug.PlatformAPI):
        _check_assignment_test_directories_are_empty(
            self.reference_tests_dir, self.args.assignments
        )

        for assignment_name in self.args.assignments:
            _generate_assignment_tests_dir(
                assignment_name,
                self.branch,
                self.args.template_org_name,
                self.reference_tests_dir,
                api,
            )


def _generate_assignment_tests_dir(
    assignment_name: str,
    branch: str,
    template_org_name: str,
    rtd: pathlib.Path,
    api: plug.PlatformAPI,
):
    """Generate the reference tests directory for a single assignment as a
    subdirectory of the reference tests dir with the same name as the
    assignment. The assignment test directory must not already exist.
    """
    assignment_test_dir = rtd / assignment_name
    assignment_test_dir.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        repo_url = _get_authed_url(assignment_name, template_org_name, api)
        template_repo = _clone_repo_to(
            repo_url, branch, workdir / assignment_name
        )
        _copy_test_classes(
            src_dir=pathlib.Path(template_repo.working_tree_dir),
            dst_dir=assignment_test_dir,
        )


def _copy_test_classes(src_dir: pathlib.Path, dst_dir: pathlib.Path) -> None:
    reference_test_classes = src_dir.rglob("*Test.java")
    for test_class in reference_test_classes:
        shutil.copy(
            src=test_class, dst=dst_dir / test_class.name,
        )


def _clone_repo_to(
    repo_url: str, branch: str, to_path: pathlib.Path,
) -> git.Repo:
    template_repo = git.Repo.clone_from(repo_url, to_path)
    template_repo.git.checkout(branch)
    return template_repo


def _get_authed_url(
    assignment_name: str, org_name: str, api: plug.PlatformAPI
) -> str:
    # FIXME temporary workaround as insert_auth is not implemented
    # in FakeAPI.get_repo_urls. Should be fixed in RepoBee 3.4.
    return api.insert_auth(
        api.get_repo_urls([assignment_name], org_name=org_name,)[0]
    )


def _check_assignment_test_directories_are_empty(
    rtd: pathlib.Path, assignment_names: List[str]
) -> None:
    if not rtd.exists():
        return

    rtd_subdirs = {
        subdir.name: subdir for subdir in rtd.iterdir() if subdir.is_dir()
    }
    for assignment_name in assignment_names:
        test_dir = rtd_subdirs.get(assignment_name)
        if test_dir and test_dir.exists():
            raise plug.PlugError(
                f"{test_dir} exists, please remove it in order "
                "to gather fresh tests for the assignment"
            )
