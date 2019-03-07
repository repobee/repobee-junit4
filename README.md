# `repomate-junit4`, a JUnit 4.12 test runner plugin for `repomate`

[![Build Status](https://travis-ci.com/slarse/repomate-junit4.svg?token=1VKcbDz66bMbTdt1ebsN&branch=master)](https://travis-ci.com/slarse/repomate-junit4)
[![Code Coverage](https://codecov.io/gh/slarse/repomate-junit4/branch/master/graph/badge.svg)](https://codecov.io/gh/slarse/repomate-junit4)
[![PyPi Version](https://badge.fury.io/py/repomate-junit4.svg)](https://badge.fury.io/py/repomate-junit4)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

This is a plugin for [repomate](https://github.com/slarse/repomate) that runs
JUnit4 test classes on production classes in a cloned student repo.

## Requirements
`repomate-junit4` has a few non-Python dependencies.

1. `java` must ba available from the command line.
2. `javac` must be available from the command line.
    - In other words, install a `JDK` version that is compatible with the files
    you intend to test!
3. `junit-4.12.jar` must be available on the `CLASSPATH` variable, or configured
    (see [Added CLI arguments](#added-cli-arguments) and
    [Configuration file](#configuration-file)).
4. `hamcrest-core-1.3.jar` must be available on the `CLASSPATH` variable or
   configured in order to make use of `hamcrest` matchers.

The `hamcrest` and `junit` jars ar available from Maven Central:

```bash
wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar
```

## Install
The recommended way to install `repomate-junit4` is with `pip`.

```bash
python3 -m pip install --user repomate-junit4
```

The plugin itself does not actually require `repomate`, but it is fairly
useless without. If `repomate` and `repomate-junit4` are both installed in the
same environment, then `repomate` should just find `repomate-junit4`.
For `repomate` to actually use `repomate-junit4`, it must be configured
in the `repomate` configuration file. Refer to the
[`repomate` docs](https://repomate.readthedocs.io/en/latest/configuration.html)
for information on the configuration file and its expected location, and the
[Configuration file](#configuration-file) section here for info on what you
need to add to it.

## Usage

### Terminology and conventions
This is terminology added in excess to that which is defined in the [`repomate`
docs](https://repomate.readthedocs.io/en/latest/fundamentals.html#terminology).
For brevity, some conventions expected by `repomate-junit4` are baked into
these definitions.

* _Production class:_ A Java file/class written in the student repo.
* _Test file_: A file ending in `Test.java` which contains a test class for
  some production class. If the students are supposed to write a file called
  `LinkedList.java`, the corresponding test class must be called
  `LinkedListTest.java`.
* _Test dir_: A directory named after a master repo, containing tests for
  student repos based on that master repo. Should contain test files
  as defined above.
* _Reference tests directory (RTD)_: A local directory containing subdirectories
  with reference tests. Each subdirectory should be a test dir as defined above.

### Security aspects
There are some inconvenient security implications to running untrusted code on
your own computer. `repomate-junit4` tries to limit what a student's code can
do by running with a very strict JVM
[Security Policy](https://docs.oracle.com/javase/7/docs/technotes/guides/security/PolicyFiles.html).
This is enforced by the Java
[SecurityManager](https://docs.oracle.com/javase/8/docs/api/java/lang/SecurityManager.html).
The policy used looks like this:

```
// empty grant to strip all permissions from all codebases
grant {
};

// the `junit-4.12.jar` needs this permission for introspection
grant codeBase "file:{junit4_jar_path}" {{
    permission java.lang.RuntimePermission "accessDeclaredMembers";
}};
"""
```

This policy disallows student code from doing most illicit things, such as
accessing files outside of the codebases's directory, or accessing the network.
The `{junit4_jar_path}` is dynamically resolved during runtime, and will lend
the actual `junit-4.12.jar` archive that is used to run the test classes
sufficient permissions to do so.

This policy seems to work well for introductory courses in Java, but there may
be snags because of how restrictive it is. If you find that some permission
should definitely be added, please
[open an issue about it](https://github.com/slarse/repomate-junit4/issues/new)
There are plans to add the ability to specify a custom security policy, but
currently, your only choice is to either use this default policy or disable it
with `--disable-security`.

> **Important:** The security policy relies on the correctness of the Java
> SecurityManager. It is probably not bulletproof, so if you have strict
> security requirements, you should probably only run this plugin inside of a
> properly secured environment (for example, a virtual machine).

### Added CLI arguments
`repomate-junit4` adds four new CLI arguments to the `repomate clone` command.

* `-rtd|--reference-tests-dir`
    - Path to the RTD.
    - **Required** unless specified in the configuration file.
* `-junit|--junit-path`
    - Path to the `junit-4.12.jar` library.
    - **Required** unless specified on the `CLASSPATH` variable, or in the
      configuration file.
* `-ham|--hamcrest-path`
    - Path to the `hamcrest-core-1.3.jar` library.
    - **Required** unless specified on the `CLASSPATH` variable, or in the
      configuration file.
* `-i|--ignore-tests`
    - A whitespace separated list of test files (e.g. `LinkedListTest.java`) to
    ignore. This is useful for example if there are abstract test classes in
    the test dir.
* `--disable-security`
    - Disable the seurity policy.
* `-v|--verbose`
    - Display more verbose information (currently only concerns test failures).
    - Long lines are truncated.
* `-vv|--very-verbose`
    - Same as `-v`, but without truncation.

### Configuration file
First and foremost, `junit4` must be added to the `plugins` option under the
`[DEFAULTS]` section in order to activate the plugin,
[see details here](https://repomate.readthedocs.io/en/latest/plugins.html#using-existing-plugins).
The `--hamcrest-path`, `--junit-path` and `--reference-tests-dir` arguments can
be configured in the standard
[`repomate` configuration file](https://repomate.readthedocs.io/en/latest/configuration.html)
by adding the `[junit4]` section heading. Example:

```bash
[DEFAULTS]
plugins = junit4

[junit4]
reference_tests_dir = /absolute/path/to/rtd
junit_path = /absolute/path/to/junit-4.12.jar
hamcrest_path = /absolute/path/to/hamcrest-core-1.3.jar
```

> **Important:** All of the paths in the config must be absolute for
> `repomate-junit4` to behave as expected.
