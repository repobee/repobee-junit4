.. _usage:

Usage
*****

For general usage of plugins, refer to

Terminology and conventions
---------------------------
``repobee-junit4`` adds some additional terminology to RepoBee that you need
to be familiar with to fully understand the rest of the documentation.

- **Production class:** A Java file/class in the student repo (written by the
  student).
- **Test class:** A Java file/class ending in ``Test.java`` containing tests
  for a namesake production class. Test classes are paired with production
  classes by simply appending ``Test`` to the production class name. For
  example, ``LinkedList.java`` would have a test class called
  ``LinkedListTest.java``.
- **Test directory:** A directory named after a template repo, containing tests
  for the assignments in that repo.
- **Reference tests directory (RTD):** A directory containing test directories
  (as defined above).

See the :ref:`use case` for a more detailed look at how all of this fits
together.

.. _cli:

CLI arguments
-------------

``repobee-junit4`` adds several new CLI arguments to the ``repos clone``
command.

* ``--junit4-reference-tests-dir``
    - Path to the RTD.
    - Can be configured
    - **Required** unless configured
* ``--junit4-junit-path``
    - Path to the JUnit4 library (any version of it, but we recommend
      ``>4.13.1``).
    - Picked up automatically if on the ``CLASSPATH`` environment variable.
    - Can be configured
    - **Required** unless configured
* ``--junit4-hamcrest-path``
    - Path to the ``hamcrest-core-1.3.jar`` library.
    - Picked up automatically if on the ``CLASSPATH`` environment variable.
    - Can be configured
    - **Required** unless configured
* ``--junit4-run-student-tests``
    - Run test classes from the student repository instead of from the
      reference tests.
    - Expects the test classes in the reference tests directory to be present
      in the student repository.
        - Only runs if all tests found in the RTD are present in the student
          repository.
        - Use in conjunction with ``--junit4-ignore-tests`` to ignore some
          tests from the RTD.
* ``--junit4-ignore-tests``
    - A whitespace separated list of test files (e.g. ``LinkedListTest.java``) to
      ignore.
* ``--junit4-disable-security``
    - Disable the security policy.
* ``--junit4-verbose``
    - Display more verbose information (currently only concerns test failures).
    - Long lines are truncated.
* ``--junit4-very-verbose``
    - Same as ``--junit4-verbose``, but without truncation.
* ``--junit4-timeout``
    - The maximum amount of time a test class is allowed to run before timing
      out. Defaults to a sane value.
    - Can be configured

.. _use case:

Example use case
----------------
Assume that we have a template repo called *fibonacci* with an assignment to
implement a method that returns the n:th Fibonacci number. The template repo
could then look like this:

.. code-block:: bash

   fibonacci
   ├── README.md
   └── src
       └── Fibo.java

To be able to test the students' implementations, we write a test class
``FiboTest.java`` and put it in our reference tests directory, in a test
directory named after the template repository. The reference test directory would
then look like this.

.. code-block:: bash

   reference_tests
   └── fibonacci
       └── FiboTest.java

.. note::

    The RTD can be generated from template repositories if the complete
    reference tests are available on any branch, see :ref:`generate_rtd`.

Now, assume that we have students *ham*, *spam* and *eggs*, and their student
repos *ham-fibonacci*, *spam-fibonacci* and *eggs-fibonacci*. Assuming that the
JUnit4 and Hamcrest jars have been configured as suggested in :ref:`config`,
and that the basic RepoBee arguments are configured (see the `RepoBee config
docs`_), we can run ``repobee clone`` with ``repobee-junit4`` activated like
this:

.. code-block:: none

   $ repobee -p junit4 clone -a fibonacci -s ham spam eggs --junit4-reference-tests-dir /path/to/reference_tests
   [INFO] cloning into student repos ...
   [INFO] Cloned into https://some-enterprise-host/some-course-org/inda-18/ham-fibonacci
   [INFO] Cloned into https://some-enterprise-host/some-course-org/inda-18/spam-fibonacci
   [INFO] Cloned into https://some-enterprise-host/some-course-org/inda-18/eggs-fibonacci
   [INFO] executing post clone hooks on repos
   [INFO] executing post clone hooks on eggs-fibonacci
   [INFO] executing post clone hooks on spam-fibonacci
   [INFO] executing post clone hooks on ham-fibonacci
   [INFO]
   hook results for spam-fibonacci

   junit4: SUCCESS
   Status.SUCCESS: Test class FiboTest passed!


   hook results for eggs-fibonacci


   junit4: ERROR
   Status.ERROR: multiple production classes found for FiboTest.java


   hook results for ham-fibonacci

   junit4: ERROR
   Status.ERROR: Test class FiboTest failed 1 tests


   [INFO] post clone hooks done

.. note::

   The output is color coded when displayed in a terminal.


Let's digest what happened here. We provided the assignment name (``-a
fibonacci``) and the reference tests directory (``--junit4-reference-tests-dir
/path/to/reference_tests``). ``repobee-junit4`` then looked in the test
directory matching the assignment name (i.e. *fibonacci*) and found a test
class ``FiboTest.java``. By the naming convention, it knows that it should now
look for a file called ``Fibo.java`` in the student repos. The following then
happened when testing the repos:

* *spam-fibonacci:* The production class ``Fibo.java`` was found and passed the
  test class.
* *eggs-fibonacci:* Multiple files called ``Fibo.java`` were found, and
  ``repobee-junit4`` did not know which one to use.

  - Duplicate class names are only allowed if their fully qualified names
    differ (i.e. the classes are in different packages).  If production code is
    supposed to be packaged, the test classes must also be packaged (in the
    same package).
* *ham-fibonacci:* The production class ``Fibo.java`` was found, but failed one
  of the tests.

    - Running the same command again with ``--junit4-verbose`` or
      ``--junit4-very-verbose`` would display which test failed, and why.

Other common causes of errors include:

- No production class found for a test class.
- Compile error.
- Security policy violation.
   - See :ref:`security`.

This concludes the use case example, I hope you found it enlightening.

.. _generate_rtd:

Generating the RTD from template repositories (``junit4 generate-rtd``)
-----------------------------------------------------------------------

This plugin comes with an auxiliary command for generating the RTD from template
repositories that contain the full test suite on some branch. For example, a
common setup may be to keep the version of a template that's pushed to student
repositories on the ``master`` branch, and the full solutions on a branch called
``solutions``.

.. note::

    See the `repobee-sanitizer plugin
    <https://github.com/repobee/repobee-sanitizer>`_ for assistance with
    maintaining a branch with complete solutions to an assignment, and one
    branch with the student's version.

Given that the reference tests are present on a branch in a template repo, the
``junit4 generate-rtd`` command can be used to extract test classes from it.
Assuming that the reference tests are on the ``solutions`` branch of the
``fibonacci`` template repo, the following command should do the
trick.

.. code-block:: bash

   $ repobee -p junit4 \
        junit4 generate-rtd \
        --assignments fibonacci \
        --students ham spam eggs \
        --reference-tests-dir /path/to/reference_tests \
        --branch solutions

Assuming ``FiboTest.java`` was present on the ``solutions``` branch, a test
directory called ``fibonacci`` should have been generated in the reference
tests directory:

.. code-block:: bash

   reference_tests
   └── fibonacci
       └── src
           └── FiboTest.java

To later generate test directories for other assignments, simply run the
command again but with other assignments (i.e. other arguments for the
``--assignments`` option).

.. important::

    Although you can generate test directories for new assignments in the same
    RTD as you have previously generated test directories for other
    assignments, you can't overwrite an existing test directory. If you need to
    update the tests for some assignments, first delete its corresponding test
    directory in the RTD.

.. _RepoBee config docs: https://repobee.readthedocs.io/en/latest/configuration.html#configuration-file
