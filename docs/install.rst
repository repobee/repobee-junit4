.. _install:

Install
*******

Requirements
------------

.. Important::

   Once you have gone through this section, you should have:

   1. Repomate installed
   2. A JDK (preferably 8+, 7 may work) installed
   3. ``junit-4.12.jar`` and ``hamcest-core-1.3.jar`` downloaded

First of all, make sure that Repomate is installed and up-to-date. For a
first-time install of Repomate, see the `Repomate install docs`_. If you
already have Repomate installed, make sure it is up-to-date.

.. code-block:: bash

   python3 -m pip install --user --upgrade repomate

Furthermore, a JDK must be installed. ``repomate-junit4`` has been extensively
tested with OpenJDK 8+, but should work well with JDK 7 and later. Make sure
that:

1. ``java`` is available from the command line.
2. ``javac`` is available from the command line.

To be able to actually run test classes, you also need the JUnit4 and Hamcrest
jars. They can be downloaded from Maven Central.

.. code-block:: bash

   wget http://central.maven.org/maven2/junit/junit/4.12/junit-4.12.jar
   wget http://central.maven.org/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar

If you don't have ``wget`` installed, just copy the links above and download
them manually.

Install plugin
--------------

To install ``repomate-junit4``, simply use ``pip`` again.

.. code-block:: bash

   python3 -m pip install --user repomate-junit4

Repomate should simply be able to find ``repomate-junit4`` if they are both
installed in the same environment. To verify that it is correctly installed,
run ``repomate -p junit4 clone -h``. You should see some additional command
line arguments added (such as ``--reference-tests-dir``). See the `Using
existing plugins`_ for more information on how to use plugins in general,
and :ref:`usage` for details on this plugin.

.. _config:

Configuration
-------------

Some options for ``repomate-junit4`` can be configured in the `Repomate
configuration file`_ by adding the ``[junit4]`` section. Everything
``repomate-junit4`` needs to operate *can* be provided on the command line, but
I strongly recommend adding the absolute paths to the ``junit-4.12.jar`` and
``hamcrest-core-1.3.jar`` files to the config file. Simply append the following
to the end of the configuration file.

.. code-block:: bash

   [junit4]
   junit_path = /absolute/path/to/junit-4.12.jar
   hamcrest_path = /absolute/path/to/hamcrest-core-1.3.jar

.. important::

   All paths in the configuration file must be absolute to behave as expected.

See :ref:`cli` for a complete list of arguments that can be configured.

.. _Repomate install docs: https://repomate.readthedocs.io/en/latest/install.html
.. _Repomate configuration file: https://repomate.readthedocs.io/en/latest/configuration.html#configuration-file
.. _Using existing plugins: https://repomate.readthedocs.io/en/latest/plugins.html#using-existing-plugins
