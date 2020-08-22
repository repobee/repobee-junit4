"""Exceptions for the junit4 plugin.

.. module:: _exception
    :synopsis: Exceptions for the junit4 plugin.

.. moduleauthor:: Simon Larsén
"""

import repobee_plug as plug

from repobee_junit4 import SECTION


class ActError(plug.PlugError):
    """Raise if something goes wrong in act_on_clone_repo."""

    def __init__(self, hook_result):
        self.hook_result = hook_result


class JavaError(ActError):
    """Raise if something goes wrong with Java files."""

    def __init__(self, msg):
        res = plug.Result(name=SECTION, status=plug.Status.ERROR, msg=msg)
        super().__init__(res)
