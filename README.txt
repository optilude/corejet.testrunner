Introduction
============

This package provides an extension to the test runner to the one that ships
with `zope.testrunner`_, as well as a buildout recipe based on
`zc.recipe.testrunner`_ to install a test script for this test runner.

It is based on (and can be used as a wholesale replacement for),
``collective.xmltestreport``.

The test runner is identical to the one in ``zope.testrunner``, except:

* it is capable of writing test reports in the XML format output by JUnit/Ant.
  This allows the test results to be analysed by tools such as the
  Hudson/Jenkins continuous integration server.
* it can output reports in the CoreJet XML format - see `corejet.core`_

Usage
=====

In your buildout, add a part like this::

    [buildout]
    parts =
        ...
        test

    ...

    [test]
    recipe = corejet.testrunner
    eggs =
        my.package
    defaults = ['--auto-color', '--auto-progress']

The recipe accepts the same options as `zc.recipe.testrunner`_, so look at
its documentation for details.

When buildout is run, you should have a script in ``bin/test`` and a directory
``parts/test``.

To run the tests, use the ``bin/test`` script. If you pass the ``--xml``
option, test reports will be written to ``parts/test/testreports`` directory::

    $ bin/test --xml -s my.package

If you are using Hudson, you can now configure the build to publish JUnit
test reports for ``<buildoutdir>/parts/test/testreports/*.xml``.

To output a CoreJet report, do::

    $ bin/test --corejet="file,path/to/corejet/file.xml" -s my.package

The CoreJet report and output XML file will be placed in
``parts/test/corejet``. You can combine ``--xml`` and ``--corejet``.

The example above uses the ``file`` CoreJet repository source, which expects
to find a CoreJet XML file at the path specified after the comma.

Repository sources
==================

Other repository sources can be registered via entry points: Packages must
register an entry point under ``corejet.repositorysource`` identifying a
callable that is passed the string *after* the comma with a unique name and
which should return a ``corejet.core.model.RequirementsCatalogue`` object.

Hence, the ``file`` source is defined as::

    def fileSource(path):
        catalogue = RequirementsCatalogue()
        with open(path) as stream:
            catalogue.populate(stream)
        return catalogue

and registered with::

    [corejet.repositorysource]
    file = corejet.testrunner.filesource:fileSource

Use ``bin/test --help`` for a full list of options.

.. _zope.testrunner: http://pypi.python.org/pypi/zope.testrunner
.. _zc.recipe.testrunner: http://pypi.python.org/pypi/zc.recipe.testrunner
.. _corejet.core: http://pypi.python.org/pypi/corejet.core
