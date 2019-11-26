.. repobee-junit4 documentation master file, created by
   sphinx-quickstart on Sun Mar 17 22:45:15 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to repobee-junit4's documentation!
===========================================
This plugin for `RepoBee <https://github.com/repobee/repobee>`_ adds a way to
run JUnit4 test classes on student repositories. It hooks into the ``clone``
command after all repos have been cloned, and executes tests on them one at a
time. It's possible both to run reference tests available only to you, and to
run tests found in the students' repositories have written themselves (with the
caveat that the students' test classes must have the same names as your
reference test classes). The documentation is quite concise, I recommend that
you go through everything but the module reference if you intend to use this
plugin.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   usage
   security
   code



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
