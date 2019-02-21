"""Utility functions for activities related to Java.

This module contains utility functions dealing with Java-specific behavior, such
as parsing package statements from Java files and determining if a class is
abstract.

.. module:: _java
    :synopsis: Utility functions for activities related to Java.

.. moduleauthor:: Simon Larsén
"""
import pathlib
import re
import os
import sys
import subprocess

from typing import Iterable, Tuple, Union, List

import repomate_plug as plug
from repomate_plug import Status

from repomate_junit4 import SECTION


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
        regex, class_.read_text(encoding=sys.getdefaultencoding()), flags=re.MULTILINE
    )
    return match is not None


def generate_classpath(*paths: pathlib.Path, classpath: str = "") -> str:
    """Return a classpath including all of the paths provided. Always appends
    the current working directory to the end.

    Args:
        paths: One or more paths to add to the classpath.
        classpath: An initial classpath to append to.
    Returns:
        a formated classpath to be used with ``java`` and ``javac``
    """
    for path in paths:
        classpath += ":{!s}".format(path)

    classpath += ":."
    return classpath


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
    return class_name if not package_name else "{}.{}".format(package_name, class_name)


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
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if proc.returncode != 0:
        status = Status.ERROR
        msg = proc.stderr.decode(sys.getdefaultencoding())
    else:
        msg = "all files compiled successfully"
        status = Status.SUCCESS

    return status, msg


def pairwise_compile(
    test_classes: List[pathlib.Path], java_files: List[pathlib.Path], classpath: str
) -> Tuple[List[plug.HookResult], List[plug.HookResult]]:
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
        A tuple of lists of HookResults on the form ``(succeeded, failed)``
    """
    # TODO refactor this beast
    failed = []
    succeeded = []
    # only use concrete test classes
    concrete_test_classes = filter(lambda t: not is_abstract_class(t), test_classes)
    for test_class in concrete_test_classes:
        package = extract_package(test_class)
        prod_class_name = test_class.name.replace("Test.java", ".java")
        try:
            prod_class_path = [
                file
                for file in java_files
                if file.name == prod_class_name and extract_package(file) == package
            ][0]
            adjacent_java_files = [
                file
                for file in prod_class_path.parent.glob("*.java")
                if not file.name.endswith("Test.java")
            ] + list(test_class.parent.glob("*Test.java"))
            status, msg = javac(
                [*adjacent_java_files], generate_classpath(classpath=classpath)
            )
            if status != Status.SUCCESS:
                failed.append(plug.HookResult(SECTION, status, msg))
            else:
                succeeded.append((test_class, prod_class_path))
        except IndexError as exc:
            failed.append(
                plug.HookResult(
                    SECTION,
                    Status.ERROR,
                    "no production class found for " + fqn(package, test_class.name),
                )
            )

    return succeeded, failed


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
