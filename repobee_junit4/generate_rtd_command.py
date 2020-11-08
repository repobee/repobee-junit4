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


class GenerateRTD(plug.Plugin, plug.cli.Command):
    __settings__ = plug.cli.command_settings(
        action=JUNIT4_COMMAND_CATEGORY.generate_rtd,
        help="generate the reference tests directory by extracting test "
        "classes from template repositories (note: alpha test)",
        description="Generate the reference tests directory from template "
        "repositories by extracting any Java test classes from the template. "
        "WARNING: This command is in alpha and behavior may change in coming "
        "updates.",
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
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = pathlib.Path(tmpdir)
            _check_assignment_test_directories_are_empty(
                self.reference_tests_dir, self.args.assignments
            )

            for assignment_name in self.args.assignments:
                assignment_test_dir = (
                    self.reference_tests_dir / assignment_name
                )
                assignment_test_dir.mkdir(parents=True, exist_ok=False)

                # TODO temporary workaround as insert_auth is not implemented
                # in FakeAPI.get_repo_urls. Should be fixed in RepoBee 3.4.
                repo_url = api.insert_auth(
                    api.get_repo_urls(
                        [assignment_name],
                        org_name=self.args.template_org_name,
                    )[0]
                )
                template_repo = git.Repo.clone_from(
                    repo_url, to_path=workdir / assignment_name,
                )
                template_repo.git.checkout(self.branch)
                reference_test_classes = (workdir / assignment_name).rglob(
                    "*Test.java"
                )
                for test_class in reference_test_classes:
                    shutil.copy(
                        src=test_class,
                        dst=assignment_test_dir / test_class.name,
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
