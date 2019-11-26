.. _install:

Install
*******

Requirements
------------

.. Important::

   Once you have gone through this section, you should have:

   1. RepoBee installed
   2. A JDK (preferably 8+, 7 may work) installed
   3. ``junit-4.12.jar`` and ``hamcest-core-1.3.jar`` downloaded

First of all, make sure that RepoBee is installed and up-to-date. For a
first-time install of RepoBee, see the `RepoBee install docs`_. If you
already have RepoBee installed, make sure it is up-to-date.

.. code-block:: bash

   python3 -m pip install --user --upgrade repobee

Furthermore, a JDK must be installed. ``repobee-junit4`` has been extensively
tested with OpenJDK 8+, but should work well with JDK 7 and later. Make sure
that:

1. ``java`` is available from the command line.
2. ``javac`` is available from the command line.

To be able to actually run test classes, you also need the JUnit4 and Hamcrest
jars. They can be downloaded from Maven Central.

.. code-block:: bash

    curl https://search.maven.org/remotecontent?filepath=junit/junit/4.12/junit-4.12.jar -o junit-4.12.jar
    curl https://search.maven.org/remotecontent?filepath=org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar -o hamcrest-core-1.3.jar

If you don't have ``curl`` installed, just copy the links above and download
them manually.

Install plugin
--------------

To install ``repobee-junit4``, simply use ``pip`` again.

.. code-block:: bash

   python3 -m pip install --user repobee-junit4

RepoBee should simply be able to find ``repobee-junit4`` if they are both
installed in the same environment. To verify that it is correctly installed,
run ``repobee -p junit4 clone -h``. You should see some additional command
line arguments added (such as ``--reference-tests-dir``). See the `Using
existing plugins`_ for more information on how to use plugins in general,
and :ref:`usage` for details on this plugin.

.. _config:

Configuration
-------------

Some options for ``repobee-junit4`` can be configured in the `RepoBee
configuration file`_ by adding the ``[junit4]`` section. Everything
``repobee-junit4`` needs to operate *can* be provided on the command line, but
I strongly recommend adding the absolute paths to the ``junit-4.12.jar`` and
``hamcrest-core-1.3.jar`` files to the config file. Simply append the following
to the end of the configuration file. Here's a sample configuration.

.. code-block:: bash

   [junit4]
   junit_path = /absolute/path/to/junit-4.12.jar
   hamcrest_path = /absolute/path/to/hamcrest-core-1.3.jar
   reference_tests_dir = /absolute/path/to/reference_tests_dir

.. important::

   All paths in the configuration file must be absolute to behave as expected.

See :ref:`cli` for a complete list of arguments that can be configured.

.. _RepoBee install docs: https://repobee.readthedocs.io/en/latest/install.html
.. _RepoBee configuration file: https://repobee.readthedocs.io/en/latest/configuration.html#configuration-file
.. _Using existing plugins: https://repobee.readthedocs.io/en/latest/plugins.html#using-existing-plugins
