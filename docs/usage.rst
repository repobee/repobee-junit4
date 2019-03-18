.. _usage:

Usage
*****

Terminology and conventions
---------------------------
``repomate-junit4`` adds some additional terminology to Repomate that you need
to be familiar with to fully understand the rest of the documentation.

- **Production class:** A Java file/class in the student repo (written by the
  student).
- **Test class:** A Java file/class ending in ``Test.java`` containing tests
  for a namesake production class. Test classes are paired with production
  classes by simply appending ``Test`` to the production class name. For
  example, ``LinkedList.java`` would have a test class called
  ``LinkedListTest.java``.
- **Test directory:** A directory named after a master repo, containing tests
  for the assignments in that repo.
- **Reference tests directory (RTD):** A directory containing test directories
  (as defined above).

See the :ref:`use case` for a more detailed look at how all of this fits
together.

.. _cli:

CLI arguments
-------------

``repomate-junit4`` adds several new CLI arguments to the ``repomate clone``
command.

* ``-rtd|--reference-tests-dir``
    - Path to the RTD.
    - Can be specified in the configuration file with the
      ``reference_test_dir`` option.
    - **Required** unless specified in the configuration file.
* ``-junit|--junit-path``
    - Path to the ``junit-4.12.jar`` library.
    - Picked up automatically if on the ``CLASSPATH`` environment variable.
    - Can be specified in the configuration file with the
      ``junit_path`` option.
    - **Required** unless specified on the ``CLASSPATH`` variable, or in the
      configuration file.
* ``-ham|--hamcrest-path``
    - Path to the ``hamcrest-core-1.3.jar`` library.
    - Picked up automatically if on the ``CLASSPATH`` environment variable.
    - Can be specified in the configuration file with the
      ``hamcrest_path`` option.
    - **Required** unless specified on the ``CLASSPATH`` variable, or in the
      configuration file.
* ``-i|--ignore-tests``
    - A whitespace separated list of test files (e.g. ``LinkedListTest.java``) to
      ignore.
* ``--disable-security``
    - Disable the security policy.
* ``-v|--verbose``
    - Display more verbose information (currently only concerns test failures).
    - Long lines are truncated.
* ``-vv|--very-verbose``
    - Same as ``-v``, but without truncation.

.. _Repomate config docs: https://repomate.readthedocs.io/en/latest/configuration.html#configuration-file
