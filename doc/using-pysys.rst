=====================================================
Using PySys to test your EPL apps
=====================================================
:Description: Document detailing the use of the PySys framework to test EPL apps locally and in the cloud.

Introduction
============

PySys is a testing framework that provides a way to test your applications. 

See `PySys Documentation <https://pysys-test.github.io/pysys-test/>`_ for details on installation and how the framework can be used and the facilities it contains. 

.. _test-in-cloud:

Testing in the Cumulocity IoT cloud
===================================

.. _setup-for-test-in-cloud:

Setup for testing in the Cumulocity IoT cloud
----------------------------------------------
You can automatically test your applications only using a Cumulocity IoT tenant with Apama EPL Apps enabled. To do this, you will need a dedicated Cumulocity IoT tenant for your testing in order to avoid disrupting any production activities. When testing within Cumulocity IoT, no Apama installation is required, just a copy of PySys, which can be installed via Pip, and a copy of this SDK.

There is an extension to PySys that is needed for the framework included in this GitHub repository, it can automatically be made available to the PySys tests by setting the EPL_TESTING_SDK environment variable. You simply need to point it to the path where you checked out this repository. 

For example, on Linux: 

.. code-block:: shell

    export EPL_TESTING_SDK=/path_to_sdk

Or for Windows:

.. code-block:: shell

    set EPL_TESTING_SDK=path_to_sdk

In order to use PySys to test your application, you will need to create a PySys project and some PySys tests under that directory. A sample project with sample tests can be found in the samples and samples-performance directories of this GitHub repository.

You can create an empty PySys project by copying the pysysproject.xml from the sample or by running:

.. code-block:: shell

    pysys makeproject

The project configuration will need to provide some configuration for how to run all of the tests. The sample projects are already configured to do this - they allow you to provide credentials for your tenant via environment variables CUMULOCITY_SERVER_URL, CUMULOCITY_USERNAME, and CUMULOCITY_PASSWORD, along with the EPL_TESTING_SDK described above.

If you start with a blank project file, you will need to add properties for these values to the pysysproject.xml file:

.. code-block:: xml

	<!-- Set to the location containing this repository -->
	<property name="EPL_TESTING_SDK" value="${env.EPL_TESTING_SDK}"/>

	<!-- Set to the location containing your EPL application monitors -->
	<property name="EPL_APPS" value="${env.EPL_APPS}" default="${env.EPL_TESTING_SDK}/samples/apps"/>

	<!-- Specify the tenant which will be used to run the tests -->
	<property name="CUMULOCITY_SERVER_URL" value="${env.CUMULOCITY_SERVER_URL}" default="https://mytenant.cumulocity.com" />

	<!-- username and password must be provided for authentication -->
	<property name="CUMULOCITY_USERNAME" value="${env.CUMULOCITY_USERNAME}" default="myUserName" />
	<property name="CUMULOCITY_PASSWORD" value="${env.CUMULOCITY_PASSWORD}" default="myPassword" />
	
	<path value="${EPL_TESTING_SDK}/testframework"/>

You can also put these properties directly in the file.

If your server URL does not specify the tenant (such as when using Cumulocity IoT Edge), then set that in the username with a /, for example, t1234567/myUserName.

Creating a test
----------------
See :doc:`Testing the performance of your EPL apps <performance-testing>` for details on creating and running performance tests.

To create a test, you can either copy an existing test (such as one of our samples) and rename it, or by running:

.. code-block:: shell
    
    pysys make TestName

If you do this, the default PySys test case comes with a run.py file. For these tests, you should remove that file, it is not needed. If you do want to use it, see the '`Advanced tests`_' section below.

A PySys test case comprises a directory with a unique name, containing a pysystest.xml and an Input directory containing your test EPL monitors. These should be written according to the :doc:`Writing tests for EPL apps <testing-epl>` document, for example, AlarmOnMeasurementThresholdTest.mon in the provided samples. In particular, they must terminate either by all the listeners terminating or with an explicit 'die' statement.

The test is configured through the pysystest.xml file. This contains the title and purpose, which you should use for a description of what your test does. You must also use it to specify how to run your test. To run a test using Apama EPL Apps in your Cumulocity IoT tenant, you must add the following block:

.. code-block:: xml

    <data>
      <class name="EPLAppsSimpleTest" module="${EPL_TESTING_SDK}/testframework/apamax/eplapplications/basetest"/>
      <user-data name="EPLApp" value="AlarmOnMeasurementThreshold"/>
    </data>

The user-data section is optional. It specifies which of the applications in your EPL_APPS directory should be used with this test case. If you don't specify it, then all the EPL apps in that directory will be injected before running this test.

Running the test
-----------------

Our sample tests are set up in the following way:

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

See :doc:`Testing the performance of your EPL apps <performance-testing>` for details on running performance tests.

Testing locally
===============

*To follow this, it is assumed that you have an Apama installation set up with the Apama PySys extensions.*

You can also test your EPL app with a locally running correlator connected to the Cumulocity IoT platform. This provides all the capabilities of running in the cloud whilst not taking valuable cloud resources. Running locally also gives you much more access to the correlator allowing some fine-tuning. 

We provide a basic correlator project that can be used to deploy your test. It has the same bundles loaded as EPL apps have access to and so will behave the same as in the cloud. 

The PySys project should be set up the same as for testing EPL apps.

In order to run your test with a local correlator, you must specify a different class to use in the data block of the test's pysystest.xml:

.. code-block:: xml

   <class name="LocalCorrelatorSimpleTest" module="${EPL_TESTING_SDK}/testframework/apamax/eplapplications/basetest"/>

Setting which EPL app to run the test on works as before.

Running the test
-----------------

To run the test using a local correlator requires the APAMA_HOME project property to be set as the path to your installation of Apama. This can be done by simply running the test in an Apama command prompt or by explicitly setting the APAMA_HOME environment variable.

The sample for running with a local correlator is as below:

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

+ All active Alarms in your Cumulocity IoT tenant are cleared.
+ Any devices created by previous tests (which are identified by the device name having prefix "PYSYS\_") are deleted from your tenant.

Advanced tests
==============

For anyone who already knows how to use PySys and wants to write Python code for their test running and validation, it is possible to also add a run.py to your test case. We provide samples of tests both running within Apama EPL Apps and with a local correlator in the advanced directory of the samples.

In order to view documentation on classes for PySys helpers for EPL Apps please see: `PySys helpers <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc/>`_

See :doc:`Testing the performance of your EPL apps <performance-testing>` for details on writing performance tests.

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
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .*', contains=False)


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
