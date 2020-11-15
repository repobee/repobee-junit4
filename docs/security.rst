.. _security:

Security aspects
****************

There are some inconvenient security implications to running untrusted code on
your own computer. ``repobee-junit4`` tries to limit what a student's code can
do by running with a very strict JVM `Security Policy`_. This is enforced by
the Java SecurityManager_. The policy used looks like this:


.. code-block:: java

   // empty grant to strip all permissions from all codebases
   grant {
   };

   // the JUnit4 jar needs this permission for introspection
   grant codeBase "file:{junit4_jar_path}" {{
       permission java.lang.RuntimePermission "accessDeclaredMembers";
   }};

This policy disallows student code from doing most illicit things, such as
accessing files outside of the codebases's directory, or accessing the network.
The ``{junit4_jar_path}`` is dynamically resolved during runtime, and will lend
the actual JUnit4 jar archive that is used to run the test classes sufficient
permissions to do so.

This policy seems to work well for introductory courses in Java, but there may
be snags because of how restrictive it is. If you find that some permission
should definitely be added, please `open an issue`_ about it. There are plans
to add the ability to specify a custom security policy, but currently, your
only choice is to either use this default policy or disable it
with `--junit4-disable-security`.

.. important::

   The security policy relies on the correctness of the Java SecurityManager.
   It is probably not bulletproof, so if you have strict security requirements,
   you should only run this plugin inside of a properly secured environment
   (for example, a virtual machine).

.. _Security Policy: https://docs.oracle.com/javase/7/docs/technotes/guides/security/PolicyFiles.html
.. _SecurityManager: https://docs.oracle.com/javase/8/docs/api/java/lang/SecurityManager.html
.. _open an issue: https://github.com/repobee/repobee-junit4/issues/new
