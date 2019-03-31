# `repobee-junit4`, a JUnit 4.12 test runner plugin for [RepoBee](https://github.com/repobee/repobee)

[![Build Status](https://travis-ci.com/repobee/repobee-junit4.svg?branch=master)](https://travis-ci.com/repobee/repobee-junit4)
[![Code Coverage](https://codecov.io/gh/repobee/repobee-junit4/branch/master/graph/badge.svg)](https://codecov.io/gh/repobee/repobee-junit4)
[![PyPi Version](https://badge.fury.io/py/repobee-junit4.svg)](https://badge.fury.io/py/repobee-junit4)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview
This is a plugin for [RepoBee](https://github.com/repobee/repobee) that runs
JUnit4 test classes on production classes in cloned student repos. It allows
teachers and teaching assistants to quickly assess the work performed by
students in a managed and fair way. The plugin hooks into the `repobee clone`
command, and executes test classes on repos when they have been cloned to disk.
A summary report is then printed to the logfile and terminal. By default, the
plugin will only report which test classes failed (and how many tests), but it
is possible to ask for more verbose output which includes detailed information
about each test failure. See this
[example use case](https://repobee-junit4.readthedocs.io/en/latest/usage.html#example-use-case)
for a more detailed look at how it works.

### Install
`repobee-junit4` is on PyPi, so `python3 -m pip install repobee-junit4` should do the
trick. See the
[install instructions](https://repobee-junit4.readthedocs.io/en/latest/install.html)
for more elaborate instructions.

### Getting started
The best way to get started with `repobee-junit4` is to head over to the
[Docs](https://repobee-junit4.readthedocs.io), where you (among
other things) will find
[install instructions](https://repobee-junit4.readthedocs.io/en/latest/install.html)
and [usage instructions](https://repobee-junit4.readthedocs.io/en/latest/usage.html).
The latter includes an
[example use case](https://repobee-junit4.readthedocs.io/en/latest/usage.html#example-use-case)
which hopefully proves useful in clarifying how `repobee-junit4` is supposed to
be used.

## Roadmap
This plugin is in the beta testing phase. It is feature-complete, but the CLI is
not yet final and may change. This is partly due to the fact that the Repmate
plugin system itself is still in beta, and may also change.

Versioning for the CLI adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The internals
of `repobee-junit4` _do not_, so this project should not be used as a library.

## License
This software is licensed under the MIT License. See the [LICENSE](LICENSE)
file for specifics.
