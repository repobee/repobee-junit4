"""Utility functions for activities related to Java.

This module contains utility functions dealing with Java-specific behavior,
such as parsing package statements from Java files and determining if a class
is abstract.

.. module:: _java
    :synopsis: Utility functions for activities related to Java.

.. moduleauthor:: Simon Larsén
"""
import pathlib
import re
import os
import sys
import subprocess
import collections

from typing import Iterable, Tuple, Union, List

import repobee_plug as plug
from repobee_plug import Status

from repobee_junit4 import SECTION
from repobee_junit4 import _exception


def is_abstract_class(class_: pathlib.Path) -> bool:
    """Check if the file is an abstract class.

    Args:
        class_: Path to a Java class file.
    Returns:
        True if the class is abstract.
    """
    assert class_.name.endswith(".java")
    regex = r"^\s*?(public\s+)?abstract\s+class\s+{}".format(class_.name[:-5])
    match = re.search(
        regex,
        class_.read_text(encoding=sys.getdefaultencoding()),
        flags=re.MULTILINE,
    )
    return match is not None


def generate_classpath(*paths: pathlib.Path, classpath: str = "") -> str:
    """Return a classpath including all of the paths provided prepended to the
    classpath. Always appends the current working directory to the end.

    Args:
        paths: One or more paths to add to the classpath.
        classpath: An initial classpath to append to.
    Returns:
        a formated classpath to be used with ``java`` and ``javac``
    """
    for path in paths:
        classpath = "{}:{}".format(path, classpath)

    classpath += ":."
    return classpath


def fqn_from_file(java_filepath: pathlib.Path) -> str:
    """Extract the expected fully qualified class name for the given java file.

    Args:
        java_filepath: Path to a .java file.
    """
    if not java_filepath.suffix == ".java":
        raise ValueError("{} not a path to a .java file".format(java_filepath))
    package = extract_package(java_filepath)
    simple_name = java_filepath.name[: -len(java_filepath.suffix)]
    return fqn(package, simple_name)


def extract_package(class_: pathlib.Path) -> str:
    """Return the name package of the class. An empty string
    denotes the default package.
    """
    assert class_.name.endswith(".java")
    # yes, $ is a valid character for a Java identifier ...
    ident = r"[\w$][\w\d_$]*"
    regex = r"^\s*?package\s+({ident}(.{ident})*);".format(ident=ident)
    with class_.open(encoding=sys.getdefaultencoding(), mode="r") as file:
        # package statement must be on the first line
        first_line = file.readline()
    matches = re.search(regex, first_line)
    if matches:
        return matches.group(1)
    return ""


def fqn(package_name: str, class_name: str) -> str:
    """Return the fully qualified name (Java style) of the class.

    Args:
        package_name: Name of the package. The default package should be an
            empty string.
        class_name: Canonical name of the class.
    Returns:
        The fully qualified name of the class.
    """
    return (
        class_name
        if not package_name
        else "{}.{}".format(package_name, class_name)
    )


def properly_packaged(path: pathlib.Path, package: str) -> bool:
    """Check if the path ends in a directory structure that corresponds to the
    package.

    Args:
        path: Path to a Java file.
        package: The name of a Java package.
    Returns:
        True iff the directory structure corresponds to the package name.
    """
    required_dir_structur = package.replace(".", os.path.sep)
    return str(path).endswith(required_dir_structur)


def extract_package_root(class_: pathlib.Path, package: str) -> pathlib.Path:
    """Return the package root, given that class_ is the path to a .java file.
    If the package is the default package (empty string), simply return a copy
    of class_.

    Raise if the directory structure doesn't correspond to the package
    statement.
    """
    _check_directory_corresponds_to_package(class_.parent, package)
    root = class_.parent
    if package:
        root = class_.parents[len(package.split("."))]
    return root


def javac(
    java_files: Iterable[Union[str, pathlib.Path]], classpath: str
) -> Tuple[str, str]:
    """Run ``javac`` on all of the specified files, assuming that they are
    all ``.java`` files.

    Args:
        java_files: paths to ``.java`` files.
        classpath: The classpath to set.
    Returns:
        (status, msg), where status is e.g. :py:const:`Status.ERROR` and
        the message describes the outcome in plain text.
    """
    command = ["javac", "-cp", classpath, *[str(path) for path in java_files]]
    proc = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if proc.returncode != 0:
        status = Status.ERROR
        msg = proc.stderr.decode(sys.getdefaultencoding())
    else:
        msg = "all files compiled successfully"
        status = Status.SUCCESS

    return status, msg


def pairwise_compile(
    test_classes: List[pathlib.Path],
    java_files: List[pathlib.Path],
    classpath: str,
) -> Tuple[List[plug.Result], List[plug.Result]]:
    """Compile test classes with their associated production classes.

    For each test class:

        1. Find the associated production class among the ``java_files``
        2. Compile the test class together with all of the .java files in
        the associated production class' directory.

    Args:
        test_classes: A list of paths to test classes.
        java_files: A list of paths to java files from the student repo.
        classpath: A base classpath to use.
    Returns:
        A tuple of lists of Results on the form ``(succeeded, failed)``
    """
    failed = []
    succeeded = []
    # only use concrete test classes
    concrete_test_classes = filter(
        lambda t: not is_abstract_class(t), test_classes
    )
    for test_class in concrete_test_classes:
        status, msg, prod_class_path = _pairwise_compile(
            test_class, classpath, java_files
        )
        if status != Status.SUCCESS:
            failed.append(plug.Result(SECTION, status, msg))
        else:
            succeeded.append((test_class, prod_class_path))

    return succeeded, failed


def get_student_test_classes(
    path: pathlib.Path, reference_test_classes: List[pathlib.Path]
) -> List[pathlib.Path]:
    """Return paths to all files that match the test classes in the
    provided list. Raises if there is more than one or no matches for any
    of the files.

    Args:
        path: Path to the repository worktree.
        reference_test_classes: A list of paths to reference test classes.
            These are assumed to be unique.
    Returns:
        A list of paths to test classes corresponding to the ones in the input
        list, but in the student repository.
    """
    filenames = {f.name for f in reference_test_classes}
    matches = [file for file in path.rglob("*") if file.name in filenames]
    _check_exact_matches(reference_test_classes, matches)
    return matches


def _check_exact_matches(
    reference_test_classes: List[pathlib.Path],
    student_test_classes: List[pathlib.Path],
) -> None:
    """Check that for every path in reference_test_classes, there is a path in
    student_test_classes with the same filename and the same package.
    """

    def by_fqn(path):
        pkg = extract_package(path)
        return fqn(pkg, path.name)

    duplicates = _extract_duplicates(student_test_classes)
    if duplicates:
        raise _exception.JavaError(
            "Duplicates of the following test classes found in student repo: "
            + ", ".join(duplicates)
        )
    if len(student_test_classes) < len(reference_test_classes):
        reference_filenames = {f.name for f in reference_test_classes}
        student_filenames = {f.name for f in student_test_classes}
        raise _exception.JavaError(
            "Missing the following test classes in student repo: "
            + ", ".join(reference_filenames - student_filenames)
        )
    package_mismatch = []
    for ref, match in zip(
        sorted(reference_test_classes, key=by_fqn),
        sorted(student_test_classes, key=by_fqn),
    ):
        expected_package = extract_package(ref)
        actual_package = extract_package(match)
        if actual_package != expected_package:
            package_mismatch.append((ref, expected_package, actual_package))
    if package_mismatch:
        errors = ", ".join(
            "Student's {} expected to have package {}, but had {}".format(
                ref.name, expected, actual
            )
            for ref, expected, actual in package_mismatch
        )
        raise _exception.JavaError("Package statement mismatch: " + errors)


def _pairwise_compile(test_class, classpath, java_files):
    """Compile the given test class together with its production class
    counterpoint (if it can be found). Return a tuple of (status, msg).
    """
    package = extract_package(test_class)
    potential_prod_classes = _get_matching_prod_classes(
        test_class, package, java_files
    )

    if len(potential_prod_classes) != 1:
        status = Status.ERROR
        msg = (
            "no production class found for "
            if not potential_prod_classes
            else "multiple production classes found for "
        ) + fqn(package, test_class.name)
        prod_class_path = None
    else:
        prod_class_path = potential_prod_classes[0]
        adjacent_java_files = [
            file
            for file in prod_class_path.parent.glob("*.java")
            if not file.name.endswith("Test.java")
        ] + list(test_class.parent.glob("*Test.java"))
        status, msg = javac(
            [*adjacent_java_files], generate_classpath(classpath=classpath)
        )
    return status, msg, prod_class_path


def _extract_duplicates(files: List[pathlib.Path]) -> List[pathlib.Path]:
    counts = collections.Counter([f.name for f in files])
    return [path for path, count in counts.items() if count > 1]


def _get_matching_prod_classes(test_class, package, java_files):
    """Find all production classes among the Java files that math the test
    classes name and the package.
    """
    prod_class_name = test_class.name.replace("Test.java", ".java")
    return [
        file
        for file in java_files
        if file.name == prod_class_name and extract_package(file) == package
    ]


def _check_directory_corresponds_to_package(path: pathlib.Path, package: str):
    """Check that the path ends in a directory structure that corresponds
    to the package prefix.
    """
    required_dir_structure = package.replace(".", os.path.sep)
    if not str(path).endswith(required_dir_structure):
        msg = (
            "Directory structure does not conform to package statement. Dir:"
            " '{}' Package: '{}'".format(path, package)
        )
        raise ValueError(msg)
