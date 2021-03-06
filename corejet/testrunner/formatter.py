from __future__ import with_statement 

import pkg_resources
import datetime
import doctest
import os
import os.path
import shutil
import socket
import traceback

from zope.dottedname.resolve import resolve

from corejet.core.interfaces import IStory
from corejet.visualization import generateReportFromCatalogue

from lxml import etree

try:
    import manuel.testing
    HAVE_MANUEL = True
except ImportError:
    HAVE_MANUEL = False


class TestSuiteInfo(object):

    def __init__(self):
        self.testCases = []
        self.errors = 0
        self.failures = 0
        self.time = 0.0

    @property
    def tests(self):
        return len(self.testCases)

    @property
    def successes(self):
        return self.tests - (self.errors + self.failures)


class TestCaseInfo(object):

    def __init__(self, test, time, testClassName, testName, failure=None,
                 error=None):
        self.test = test
        self.time = time
        self.testClassName = testClassName
        self.testName = testName
        self.failure = failure
        self.error = error

def get_test_class_name(test):
    """Compute the test class name from the test object."""
    return "%s.%s" % (test.__module__, test.__class__.__name__, )


def filename_to_suite_name_parts(filename):
    # lop off whatever portion of the path we have in common
    # with the current working directory; crude, but about as
    # much as we can do :(
    filenameParts = filename.split(os.path.sep)
    cwdParts = os.getcwd().split(os.path.sep)
    longest = min(len(filenameParts), len(cwdParts))
    for i in range(longest):
        if filenameParts[i] != cwdParts[i]:
            break

    if i < len(filenameParts) - 1:

        # The real package name couldn't have a '.' in it. This
        # makes sense for the common egg naming patterns, and
        # will still work in other cases

        suiteNameParts = []
        for part in reversed(filenameParts[i:-1]):
            if '.' in part:
                break
            suiteNameParts.insert(0, part)

        # don't lose the filename, which would have a . in it
        suiteNameParts.append(filenameParts[-1])
        return suiteNameParts


def parse_doc_file_case(test):
    if not isinstance(test, doctest.DocFileCase):
        return None, None, None

    filename = test._dt_test.filename
    suiteNameParts = filename_to_suite_name_parts(filename)
    testSuite = 'doctest-' + '-'.join(suiteNameParts)
    testName = test._dt_test.name
    testClassName = '.'.join(suiteNameParts[:-1])
    return testSuite, testName, testClassName


def parse_doc_test_case(test):
    if not isinstance(test, doctest.DocTestCase):
        return None, None, None

    testDottedNameParts = test._dt_test.name.split('.')
    testClassName = get_test_class_name(test)
    testSuite = testClassName = '.'.join(testDottedNameParts[:-1])
    testName = testDottedNameParts[-1]
    return testSuite, testName, testClassName


def parse_manuel(test):
    if not (HAVE_MANUEL and isinstance(test, manuel.testing.TestCase)):
        return None, None, None
    filename = test.regions.location
    suiteNameParts = filename_to_suite_name_parts(filename)
    testSuite = 'manuel-' + '-'.join(suiteNameParts)
    testName = suiteNameParts[-1]
    testClassName = '.'.join(suiteNameParts[:-1])
    return testSuite, testName, testClassName


def parse_unittest(test):
    testId = test.id()
    if testId is None:
        return None, None, None
    testClassName = get_test_class_name(test)
    testSuite = testClassName
    testName = testId[len(testClassName)+1:]
    return testSuite, testName, testClassName


class CoreJetOutputFormattingWrapper(object):
    """Output formatter which delegates to another formatter for all
    operations, but also prepares an element tree of test output.
    """

    def __init__(self, delegate, cwd):
        self.delegate = delegate
        self._testSuites = {} # test class -> list of test names
        self.cwd = cwd

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def test_failure(self, test, seconds, exc_info):
        self._record(test, seconds, failure=exc_info)
        return self.delegate.test_failure(test, seconds, exc_info)

    def test_error(self, test, seconds, exc_info):
        self._record(test, seconds, error=exc_info)
        return self.delegate.test_error(test, seconds, exc_info)

    def test_success(self, test, seconds):
        self._record(test, seconds)
        return self.delegate.test_success(test, seconds)

    def _record(self, test, seconds, failure=None, error=None):
        
        try:
            os.getcwd()
        except OSError:
            # In case the current directory is no longer available fallback to
            # the default working directory.
            os.chdir(self.cwd)

        for parser in [parse_doc_file_case,
                       parse_doc_test_case,
                       parse_manuel,
                       parse_unittest]:
            testSuite, testName, testClassName = parser(test)
            if (testSuite, testName, testClassName) != (None, None, None):
                break

        if (testSuite, testName, testClassName) == (None, None, None):
            raise TypeError(
                "Unknown test type: Could not compute testSuite, testName, "
                "testClassName: %r" % test)

        suite = self._testSuites.setdefault(testSuite, TestSuiteInfo())
        suite.testCases.append(TestCaseInfo(
            test, seconds, testClassName, testName, failure, error))

        if failure is not None:
            suite.failures += 1

        if error is not None:
            suite.errors += 1

        if seconds:
            suite.time += seconds

    def writeXMLReports(self, properties={}):

        timestamp = datetime.datetime.now().isoformat()
        hostname = socket.gethostname()

        workingDir = os.getcwd()
        reportsDir = os.path.join(workingDir, 'testreports')
        if not os.path.exists(reportsDir):
            os.mkdir(reportsDir)

        for name, suite in self._testSuites.items():
            filename = os.path.join(reportsDir, name + '.xml')

            testSuiteNode = etree.Element('testsuite')

            testSuiteNode.set('tests', str(suite.tests))
            testSuiteNode.set('errors', str(suite.errors))
            testSuiteNode.set('failures', str(suite.failures))
            testSuiteNode.set('hostname', hostname)
            testSuiteNode.set('name', name)
            testSuiteNode.set('time', str(suite.time))
            testSuiteNode.set('timestamp', timestamp)

            propertiesNode = etree.Element('properties')
            testSuiteNode.append(propertiesNode)

            for k, v in properties.items():
                propertyNode = etree.Element('property')
                propertiesNode.append(propertyNode)

                propertyNode.set('name', k)
                propertyNode.set('value', v)

            for testCase in suite.testCases:
                testCaseNode = etree.Element('testcase')
                testSuiteNode.append(testCaseNode)

                testCaseNode.set('classname', testCase.testClassName)
                testCaseNode.set('name', testCase.testName)
                testCaseNode.set('time', str(testCase.time))

                if testCase.error:
                    errorNode = etree.Element('error')
                    testCaseNode.append(errorNode)

                    try:
                        excType, excInstance, tb = testCase.error
                        errorMessage = str(excInstance)
                        stackTrace = ''.join(traceback.format_tb(tb))
                    finally: # Avoids a memory leak
                        del tb

                    errorNode.set('message', errorMessage.split('\n')[0])
                    errorNode.set('type', str(excType))
                    errorNode.text = errorMessage + '\n\n' + stackTrace

                if testCase.failure:

                    failureNode = etree.Element('failure')
                    testCaseNode.append(failureNode)

                    try:
                        excType, excInstance, tb = testCase.failure
                        errorMessage = str(excInstance)
                        stackTrace = ''.join(traceback.format_tb(tb))
                    finally: # Avoids a memory leak
                        del tb

                    failureNode.set('message', errorMessage.split('\n')[0])
                    failureNode.set('type', str(excType))
                    failureNode.text = errorMessage + '\n\n' + stackTrace

            # XXX: We don't have a good way to capture these yet
            systemOutNode = etree.Element('system-out')
            testSuiteNode.append(systemOutNode)
            systemErrNode = etree.Element('system-err')
            testSuiteNode.append(systemErrNode)

            # Write file
            outputFile = open(filename, 'w')
            outputFile.write(etree.tostring(testSuiteNode, pretty_print=True))
            outputFile.close()
    
    def writeCoreJetReports(self, source, directory=None, filename='corejet.xml'):

        # corejet.robot registers CoreJet-adapters for Robot Framework tests
        # XXX: there should be a more dynamic way to configure plugin adapters
        try:
            import corejet.robot
        except ImportError:
            pass
        
        try:
            sourceType, sourceOptions = source.split(',', 1)
        except ValueError:
            # need more than 1 value to unpack
            sourceType = source.strip()
            sourceOptions = ''
        
        # Prepare output directory
        if directory is None:
            workingDir = os.getcwd()
            directory = os.path.join(workingDir, 'corejet')
        
        print "Writing CoreJet report to %s" % directory
        
        functionName = None
        
        for ep in pkg_resources.iter_entry_points('corejet.repositorysource'):
            if ep.name == sourceType and len(ep.attrs) > 0:
                functionName = "%s.%s" % (ep.module_name, ep.attrs[0],)
                break
        
        if not functionName:
            raise ValueError("Unknown CoreJet source type %s" % sourceType)
        
        sourceFunction = resolve(functionName)
        catalogue = sourceFunction(sourceOptions)
        
        # Set test time
        catalogue.testTime = datetime.datetime.now()
        
        # Find everything we've done so far
        
        testedStories = {} # story name -> {scenario name -> (scenario, info)}
        
        for suiteInfo in self._testSuites.values():
            for caseInfo in suiteInfo.testCases:
                # look up the story for the test through adaptation:
                # - for @story-decorated test, the class implements IStory
                # - for others, the test case may have an adapter for IStory
                story = IStory(caseInfo.test,
                               IStory(caseInfo.test.__class__, None))
                if not story:
                    continue
                scenarios = testedStories.setdefault(story.name.strip().lower(), {})
                
                # XXX: Relying on _testMethodName here is not very good
                scenario = getattr(story, caseInfo.test._testMethodName).scenario
                scenarios[scenario.name.strip().lower()] = (scenario, caseInfo,)

        # Allocate a status to each scenario
        for epic in catalogue.epics:
            for story in epic.stories:
                
                testedStory = testedStories.get(story.name.strip().lower(), {})
                
                for scenario in story.scenarios:
                    scenario.status = "pending"
                    
                    testedScenario, info = testedStory.get(scenario.name.strip().lower(), (None, None,))
                    
                    # Check for pass/fail
                    if info is not None:
                        if info.failure or info.error:
                            scenario.status = "fail"
                        else:
                            scenario.status = "pass"
                        
                        # Init 'global' steps when they are missing
                        setattr(story, "givens", getattr(story, "givens", []))
                        setattr(story, "thens", getattr(story, "thens", []))
                        setattr(story, "givens", getattr(story, "givens", []))

                        # Check for mismatch
                        if (
                            len(story.givens + scenario.givens) != len(testedScenario.givens) or
                            len(story.whens + scenario.whens) != len(testedScenario.whens) or
                            len(story.thens + scenario.thens) != len(testedScenario.thens)
                        ):
                            scenario.status = "mismatch"
                        
                        if scenario.status != "mismatch":
                            for left, right in zip(story.givens + scenario.givens,
                                                   testedScenario.givens):
                                if left.text.strip().lower() != right.text.strip().lower():
                                    scenario.status = "mismatch"
                                    break
                        
                        if scenario.status != "mismatch":
                            for left, right in zip(story.whens + scenario.whens,
                                                   testedScenario.whens):
                                if left.text.strip().lower() != right.text.strip().lower():
                                    scenario.status = "mismatch"
                                    break
                        
                        if scenario.status != "mismatch":
                            for left, right in zip(story.thens + scenario.thens,
                                                   testedScenario.thens):
                                if left.text.strip().lower() != right.text.strip().lower():
                                    scenario.status = "mismatch"
                                    break
        
        # TODO: We don't handle superfluous tests yet
        
        if os.path.exists(directory):
            shutil.rmtree(directory)
            
        os.mkdir(directory)
        
        # Write CoreJet file
        with open(os.path.join(directory, filename), 'w') as output:
            catalogue.write(output)
        
        # Generate HTML report
        generateReportFromCatalogue(catalogue, directory)
