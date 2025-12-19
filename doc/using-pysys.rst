=====================================================
Using PySys to test your EPL apps
=====================================================
:Description: Document detailing the use of the PySys framework to test EPL apps locally and in the cloud.

Introduction
============

This topic describes two approaches to EPL app testing:

#. `Testing in the Cumulocity cloud`_, without requiring a local installation of Apama
#. `Testing locally`_, with a correlator that runs in the same container (or machine) where Apama is installed. This is great for cases such as `testing performance <performance-testing.rst#testing-the-performance-of-your-epl-apps-and-smart-rules>`_, and provides easier access to logs and EPL debugging tools. You can even use it with the `-XpauseDuringTest` command line for locally interacting with your correlator.

Both approaches use PySys, a testing framework that provides a way to test your applications. See `PySys Documentation <https://pysys-test.github.io/pysys-test>`_ for details on installation and how the framework can be used and the facilities it contains.

.. _test-in-cloud:

Testing in the Cumulocity cloud
===================================

.. _setup-for-test-in-cloud:

Setup for testing in the Cumulocity cloud
----------------------------------------------
You can automatically test your applications only using a Cumulocity tenant with Apama EPL Apps enabled, without a local installation of Apama. 
To do this you just need Python and an installation of PySys, which can be installed using `pip install pysys`, and a copy of this SDK.

You will need to use a dedicated Cumulocity tenant for testing in order to avoid disrupting any production activities. 

There is an extension to PySys that is needed for the framework included in this GitHub repository, it can automatically be made available to the PySys tests by setting the `EPL_TESTING_SDK` environment variable. You simply need to point it to the path where you checked out this repository, for example: 

.. code-block:: shell

    export EPL_TESTING_SDK=/path_to_sdk

In order to use PySys to test your application, you will need to create a PySys project and some PySys tests under that directory. A sample project with sample tests can be found in the `samples/` and `samples-performance/` directories of this GitHub repository.

You can create an empty PySys project by creating a new directory and copying in the `pysysproject.xml` from the sample project. The sample project contains the essential configuration necessary for testing with Apama and Cumulocity.

If desired, you can set the `clearAllActiveAlarmsDuringTenantPreparation` property to `false` in the `pysysproject.xml` file to disable the default behavior of clearing all active alarms.

Creating a test
----------------
See `Testing the performance of your EPL apps and smart rules <performance-testing.rst#testing-the-performance-of-your-epl-apps-and-smart-rules>`_ for details on creating and running performance tests.

To create a test, you can either copy an existing test (such as one of our samples) and rename it, or by running:

.. code-block:: shell
    
    pysys make TestName

If you do this, the default PySys test case comes with a run.py file. For these tests, you should remove that file, it is not needed. If you do want to use it, see the '`Advanced tests`_' section below.

A PySys test case comprises a directory with a unique name, containing a pysystest.xml and an Input directory containing your test EPL monitors. These should be written according to the `Writing tests for EPL apps <testing-epl.rst#writing-tests-for-epl-apps>`_ document, for example, AlarmOnMeasurementThresholdTest.mon in the provided samples. In particular, they must terminate either by all the listeners terminating or with an explicit 'die' statement.

The test is configured through the pysystest.xml file. This contains the title and purpose, which you should use for a description of what your test does. You must also use it to specify how to run your test. To run a test using Apama EPL Apps in your Cumulocity tenant, you must add the following block:

.. code-block:: xml

    <data>
      <class name="EPLAppsSimpleTest" module="${EPL_TESTING_SDK}/testframework/apamax/eplapplications/basetest"/>
      <user-data name="EPLApp" value="AlarmOnMeasurementThreshold"/>
    </data>

The user-data section is optional. It specifies which of the applications in your EPL_APPS directory should be used with this test case. If you don't specify it, then all the EPL apps in that directory will be injected before running this test.

Running the test
-----------------

Our sample tests are set up in the following way::

	| +-samples
	| +---pysysproject.xml
	| +---apps
	| +-----AlarmOnMeasurementThreshold.mon
	| +---TestInEPLApps
	| +-----Input
	| +-------AlarmOnMeasurementThresholdTest.mon
	| +-----pysystest.xml

Run the test from within the samples directory by using the following command:

.. code-block:: shell

    pysys run TestInEPLApps

You can run your tests in the same way. If you don't provide the name of a test, PySys will run all the tests in that directory.

Whenever you run a test in the cloud, before the test is executed:

+ All active Alarms in your tenant are cleared.
+ Any EPL apps that have previously been uploaded by the framework (which have either the "PYSYS\_" or "PYSYS_TEST\_" prefix in their name) are deleted from your tenant.
+ Any devices created by previous tests (which are identified by the device name having prefix "PYSYS\_") are deleted from your tenant.

Any other existing EPL apps, analytics builder models, devices, or historic data in your tenant should be unaffected by the test run. However, to avoid any potential interference between your tests and other EPL apps that may be running in your tenant, it is recommended that you use a dedicated (clean) tenant for running your tests. 

After the test has finished, any EPL apps that were uploaded to your tenant by the test are deactivated. 

See `Testing the performance of your EPL apps and smart rules <performance-testing.rst#testing-the-performance-of-your-epl-apps-and-smart-rules>`_ for details on running performance tests.

Testing locally
===============

You can also test your EPL app with a locally running correlator connected to the Cumulocity platform. This provides all the capabilities of running in the cloud whilst not taking valuable cloud resources. 
More importantly, running locally also gives you full control over the correlator, including easier access to the logs and the chance to enable debugging and profiling options. 

The recommended way to do local testing is to start new projects by copying the `Apama sample repository template <https://github.com/Cumulocity-IoT/streaming-analytics-sample-repo-template>`_ and following the instructions it contains. 
This gives you an Apama project pre-configured with the same EPL bundles that all EPL Apps have available, as well as a PySys test project configuration you can use for your tests. 

You just need to follow the instructions given in the template readme to set the environment variables for your Cumulocity cloud tenant's `CUMULOCITY_SERVER_URL`, `CUMULOCITY_USERNAME` and `CUMULOCITY_PASSWORD` using the `c8y-vars` file. 
For security reasons, be sure to avoid committing the password into your repository. 
If you are not using the template, you will need to manually set the same environment variables, as well as the `EPL_TESTING_SDK` environment variable, and create a PySys project by copying a `pysysproject.xml` file from any project that uses EPL Apps.

The template comes with a local test called `TestLocalCorrelator` which is a great starting point. If you want an easy way to start your EPL App for local debugging and experimentation, run the test with the `pysys run -XpauseDuringTest` command line option, which will cause it to pause once the application has been injected and before it is cleaned up. 

Additional sample tests for both local and cloud testing can be found in the `samples/` and `samples-performance/` directories of the `EPL Apps Tools GitHub repository <https://github.com/Cumulocity-IoT/apama-eplapps-tools>`.

When creating new tests you can copy and existing test or create a new one. If you create a new one, in order to run your test with a local correlator, you must specify a different class to use in the data block of the test's `pysystest.xml`:

.. code-block:: xml

   <class name="LocalCorrelatorSimpleTest" module="${EPL_TESTING_SDK}/testframework/apamax/eplapplications/basetest"/>

Setting which EPL app to run the test on works as before.

Notifications 2.0
--------------------
The EPL apps test framework supports using the new Notifications 2.0 API for receiving notifications from Cumulocity. By default, this is disabled.

See `the release note <https://cumulocity.com/apama/docs/latest/change-logs/#10.15/cumulocity-10155-clientbundledeprecated>`_ for more information about the Notifications 2.0 integration.

To enable it within the EPL apps test framework, add the following elements to your PySys Project XML:

.. code-block:: xml

	<!-- Whether Notifications 2.0 is enabled. By default, it is disabled. -->
	<property name="CUMULOCITY_NOTIFICATIONS_2" value="${env.CUMULOCITY_NOTIFICATIONS_2}" default="true" />

	<!-- The Cumulocity Notifications 2.0 Service URL -->
	<property name="CUMULOCITY_NOTIFICATIONS_SERVICE_URL" value="${env.CUMULOCITY_NOTIFICATIONS_SERVICE_URL}" default="" />

Running the test
-----------------

A sample for running with a local correlator is located in the following location in this repository::

	| +-samples
	| +---pysysproject.xml
	| +---apps
	| +-----AlarmOnMeasurementThreshold.mon
	| +---TestLocalCorrelator
	| +-----Input
	| +-------AlarmOnMeasurementThresholdTest.mon
	| +-----pysystest.xml

Run the test from within the samples directory by using the following command:

.. code-block:: shell

    pysys run TestLocalCorrelator

Whenever you run a test using a local correlator, before the test is executed:

+ All active Alarms in your Cumulocity tenant are cleared.
+ Any devices created by previous tests (which are identified by the device name having prefix "PYSYS\_") are deleted from your tenant.

Note: We assume you are running the tests from an Apama container, but if not you need to set the `APAMA_HOME` environment variable to the location of your Apama installation. 

Advanced tests
==============

For anyone who already knows how to use PySys and wants to write Python code for their test running and validation, it is possible to also add a `pysystest.py` Python file to your test case. 
We provide samples of tests both running within Apama EPL Apps and with a local correlator in the advanced directory of the samples.

In order to view documentation on classes for PySys helpers for EPL Apps please see: `PySys helpers <https://cumulocity-iot.github.io/apama-eplapps-tools>`_ .

See `Testing the performance of your EPL apps and smart rules <performance-testing.rst#testing-the-performance-of-your-epl-apps-and-smart-rules>`_ for details on writing performance tests.

To run in Apama EPL Apps, your run.py should look something like this:

.. code-block:: python

 from apamax.eplapplications.basetest import ApamaC8YBaseTest
 class PySysTest(ApamaC8YBaseTest):

	def execute(self):

		# connect to the platform
		self.platform = CumulocityPlatform(self)
		eplapps = EPLApps(self.platform.getC8YConnection())

		# deploy the application
		eplapps.deploy(os.path.join(self.project.EPL_APPS, "AlarmOnMeasurementThreshold.mon"), name='AppUnderTest', activate=True, redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.AppUnderTest')

		# deploy the test
		eplapps.deploy(os.path.join(self.input, 'AlarmOnMeasurementThresholdTest.mon'), name='TestCase', description='Test case, injected by test framework', activate=True, redeploy=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.TestCase')

		# wait until the test completes
		self.waitForGrep(self.platform.getApamaLogFile(), expr="Removed monitor eplfiles.TestCase")
		
	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)


To run with a local correlator, it should look something like this:

.. code-block:: python

 from apamax.eplapplications.basetest import ApamaC8YBaseTest
 class PySysTest(ApamaC8YBaseTest):

	def execute(self):

		# create a project with C8Y bundles
		project = self.createProject("c8y-basic")
		self.addC8YPropertiesToProject(project)
		
		# copy EPL app to be tested to the project's monitors dir
		self.copy(self.project.EPL_APPS+"/AlarmOnMeasurementThreshold.mon", project.monitorsDir()+"/AlarmOnMeasurementThreshold.mon")
		# copy EPL test file from Input dir to project's monitors dir 
		self.copy(self.input+"/AlarmOnMeasurementThresholdTest.mon", project.monitorsDir()+"/AlarmOnMeasurementThresholdTest.mon")
		
		project.deploy()

		# start local correlator
		correlator = CorrelatorHelper(self, name='c8y-correlator')		
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())
		
		# wait for all events to be processed
		correlator.flush()
		
		# wait until the correlator gets a complete
		self.waitForGrep('c8y-correlator.log', expr="Removed monitor AlarmOnMeasurementThresholdTest")
		
	def validate(self):
		# look for log statements in the correlator log file
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)
