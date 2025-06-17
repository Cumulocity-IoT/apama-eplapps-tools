========================================================
Testing the performance of your EPL apps and smart rules
========================================================
:Description: Guide for using the PySys framework to test the performance of your EPL apps and smart rules.

Introduction
============

An EPL app or a smart rule can be either tested against real devices or simulated devices with simulated data. Thus writing a performance test will generally involve:

+ Creating a test.
+ Defining the test options.
+ Preparing the Cumulocity tenant.
+ Creating device simulators (if applicable).
+ Deploying EPL apps.
+ Deploying smart rules.
+ Sending measurements, events or alarms.
+ Monitoring the performance.
+ Generating the performance reports.
+ Writing a test for a multi-tenant microservice.

This document demonstrates the common process involved in writing a performance test for your existing EPL apps and smart rules. The performance tests described in the document use the EPL apps SDK based on the PySys test framework. See the `PySys documentation <https://pysys-test.github.io/pysys-test>`_  for details on the installation, and how the framework can be used and the facilities it contains. Set up the EPL apps SDK by following the steps mentioned in `Testing in the Cumulocity cloud <using-pysys.rst#testing-in-the-cumulocity-cloud>`_.

Writing a performance test
===========================

Creating a test
-------------------------
A PySys test case comprises a directory with a unique name, containing a pysystest.xml file and an Input directory containing your application-specific resources.

To create the test, you can either copy an existing test (such as one from the samples-performance or smartrules-performance directory) and rename it, or by running the following:

.. code-block:: shell
    
    pysys make TestName

The run.py file of the test contains the main logic of the test. The ``PySysTest`` class of a performance test should extend the ``apamax.eplapplications.perf.basetest.ApamaC8YPerfBaseTest`` class which provides convenient methods for performance monitoring and reporting.

.. code-block:: python

    from apamax.eplapplications.perf.basetest import ApamaC8YPerfBaseTest

    class PySysTest(ApamaC8YPerfBaseTest):
        def execute(self):
            ...
        
        def validate(self):
            super(PySysTest, self).validate()


Defining the test options
---------------------------
A test may define options such as test duration, or measurement types that you might want to change or override when running the test. To define an option, define a static attribute on the test class and provide a default value. For example:

.. code-block:: python

    class PySysTest(ApamaC8YPerfBaseTest):
        # Can be overridden at runtime, for example: 
        # pysys run -XmyTestDuration=10
        myTestDuration = 60.0

        # The type of measurements the app listens for.
        measurementType = 'type_device_temperature'

        def execute(self):
            self.log.info(f'Using measurementType = {self.measurementType} and myTestDuration = {self.myTestDuration}')
            ... 

Once the default value is defined with a static attribute, you can override the value when you run your test using the ``-X`` option:

.. code-block:: shell
    
    pysys run -XmyTestDuration=10 -XmeasurementType="MyMeasurement"

See the `PySys test options <https://pysys-test.github.io/pysys-test/pysys/UserGuide.html#configuring-and-overriding-test-options>`_ in the PySys documentation for details on configuring and overriding test options.

Preparing the Cumulocity tenant
------------------------------------
The performance test must make sure that the Cumulocity tenant used for testing the EPL app or smart rule is prepared. This is done by calling the ``prepareTenant`` method before the EPL apps or smart rules are deployed.

The ``prepareTenant`` method performs the following actions:

+ Deletes any test devices created by previous tests (which are identified by the device name having the prefix "PYSYS\_") from your tenant.
+ Deletes any test EPL apps (which have "PYSYS\_" prefix in their name) and smart rules that have previously been uploaded by the framework from your tenant.
+ Clears all active alarms in your tenant.
+ Optionally, restarts the Apama-ctrl microservice.

The ``prepareTenant`` method must be called at the start of the test before any EPL apps or smart rules are deployed. If the test is testing the same EPL app or smart rule with different configurations, then the tenant must be prepared before each iteration.

It is recommended to restart the Apama-ctrl microservice when preparing a tenant so that resources like memory are not influenced by any previous test runs.

The ``prepareTenant`` method does not delete any of the user-uploaded EPL apps and smart rules, or user-created devices. The user should disable any user-uploaded EPL apps or smart rules which can interfere with the performance test, for example, by producing or updating data that are consumed by the EPL apps or smart rules being tested. It may be prudent to disable all existing EPL apps or smart rules from the tenant for accurate performance numbers.

Creating device simulators
---------------------------
If the test needs to use simulated devices, then they can be easily created within the test. A device can be created by calling the ``createTestDevice`` method. 

All created devices are prefixed with "PYSYS\_" for identifying the devices that have been created from the test and keeping them distinct from user-created devices. Due to the prefix, all devices created using the ``createTestDevice`` method are deleted when the ``prepareTenant`` method is called. 

If devices are created without using the ``createTestDevice`` method, then make sure to have the device names prefixed with "PYSYS\_" so that they can be deleted when a tenant is prepared for a performance test run.

Deploying EPL apps
-------------------
EPL apps can be deployed by using the ``deploy`` method of the ``EPLApps`` class. The field ``eplapps`` of type ``EPLApps`` is available for performance tests.

The performance test may need to customize EPL apps for performance testing, for example, defining the threshold limit, or the type of measurements to listen for. The performance test may also test EPL apps for multiple values of some parameters in a single test or across multiple tests. One approach to customize EPL apps for testing is to use placeholder replacement strings in EPL apps and then replace the strings with actual values before deploying them to Cumulocity. For example::

    monitor MySimpleApp {
        constant float THRESHOLD := @MEASUREMENT_THRESHOLD@;
        constant string MEAS_TYPE := "@MEASUREMENT_TYPE@";
        ...
    }

In the above example app, the values of the ``THRESHOLD`` and ``MEAS_TYPE`` constants are placeholder strings that need to be replaced by the performance test. It is recommended to surround the replacement strings with some marker characters so that they are distinct from normal strings.

The ``copyWithReplace`` method creates a copy of the source file by replacing the placeholder strings with the replacement values.

For example, the above EPL app can be configured and deployed as follows:

.. code-block:: python

    # Create a dictionary with replacement strings.
    appConfiguration = {
        'MEASUREMENT_THRESHOLD': '100.0',
        'MEASUREMENT_TYPE': 'myMeasurements',
    }
    # Replace placeholder strings with replacement values and create 
    # a copy of the EPL app to the test's output directory.
    # Specify that the marker character for placeholder strings is '@' 
    self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'MyApp.mon'), 
            os.path.join(self.output, 'MyApp.mon'), replacementDict=appConfiguration, marker='@')
    
    # Deploy the EPL app with replaced values.
    self.eplapps.deploy(os.path.join(self.output, "MyApp.mon"), name='PYSYS_MyApp', redeploy=True, 
            description='Application under test, injected by test framework')

Replacement values can also come from test options so that they can be overridden when running tests. See `Defining the test options`_ for more details.

**Note:** It is recommended to prefix the names of the EPL apps with "PYSYS\_" when deploying them. This allows all EPL apps deployed during the tests to be disabled at the end of the test and deleted when preparing the tenant for a test run.

Deploying smart rules 
----------------------
Smart rules can be deployed by using the ``deploy`` method of the ``SmartRule`` class object. The ``Smartrule`` object can be built by using the ``build_<smartrulename>`` method of the ``SmartRulesManager`` class. 
The field ``smartRulesManager`` of type ``SmartRulesManager`` object is available for performance tests.

For example, the ``onMeasurementExplicitThresholdCreateAlarm`` smart rule can be configured and deployed as follows:

.. code-block:: python

    # Deploy the sample app.
    smartRule = self.smartRulesManager.build_onMeasurementExplicitThresholdCreateAlarm(
        fragment= "MyFragment",
        series="MySeries",
        rangeMin=0,
        rangeMax=100,
        alarmType="MyAlarm",
        alarmText="This is my smart rule alarm",
    )
    smartRule.deploy()

**Note:** The names of the smart rules are by default prefixed with "PYSYS\_". This allows all smart rules deployed during the tests to be disabled at the end of the test and deleted when preparing the tenant for a test run.

Sending measurements
--------------------
A performance test can either use real-time measurements from real devices or simulated measurements from simulated devices. To generate simulated measurements, the test can start measurement simulators to publish simulated measurements to Cumulocity at a specified rate which are then consumed by the EPL apps or smart rules being tested.

Different tests may have different requirements for the measurements being published. For example, a test may want to customize the type of measurements or range of measurement values. To support such requirements, the framework requires tests to define a measurement creator class to create measurements of desired types. A measurement simulator uses a measurement creator object to create measurements to publish to Cumulocity.

The following example shows a test defining a measurement creator class to create measurements within a configurable range:

.. code-block:: python

    # In the 'creator.py' file in the test Input directory.
    import random
    from apamax.eplapplications.perf import ObjectCreator

    class MyMeasurementCreator(ObjectCreator):
        def __init__(lowerBound, upperBound):
            self.lowerBound = lowerBound
            self.upperBound = upperBound

        def createObject(self, device, time):
            return {
                'time': time,
                "type": 'my_measurement',
                "source": { "id": device },
                'my_fragment': {
                    'my_series': {
                        "value": random.uniform(self.lowerBound, self.upperBound)
                    }
                }
            }

Once the measurement creator class is defined, the test can start a measurement simulator process to generate measurements for specified devices with a specified rate per device by calling the ``startMeasurementSimulator`` method. The test needs to pass the path to the Python file containing the measurement creator class, the name of the measurement creator class, and the values for the constructor parameters. 

For example, a test can use the above measurement creator class to generate measurements in the range of 50.0 to 100.0:

.. code-block:: python

    # In the run.py file of the test
    class PySysTest(ApamaC8YPerfBaseTest):
        ...
        def execute(self):
            ...
            self.startMeasurementSimulator(
                ['12345', '12346'],         # Device IDs
                1,                          # The rate of measurements to publish per device per second
                f'{self.input}/creator.py', # The Python file path containing the MyMeasurementCreator class
                'MyMeasurementCreator',     # The name of the measurement class
                [50, 100],                  # The constructor parameters for the MyMeasurementCreator class
            )
            ...

Sending events
--------------------
A performance test that consumes events can either use real-time events from real devices or simulated events from simulated devices. To generate simulated events, the test can start event simulators to publish simulated events to Cumulocity at a specified rate which are then consumed by the EPL apps or smart rules being tested.

Different tests may have different requirements for the events being published. For example, a test may want to customize the type of events. To support such requirements, the framework requires tests to define an event creator class to create events of desired types. An event simulator uses an event creator object to create events to publish to Cumulocity.

The following example shows a test defining an event creator class to create position update events within a configurable range of longitude and latitude:

.. code-block:: python

    # In the 'creator.py' file in the test Input directory.
    import random
    from apamax.eplapplications.perf import ObjectCreator

    class MyEventCreator(ObjectCreator):
        def __init__(self, lang_upper_bound, lang_lower_bound, lat_upper_bound, lat_lower_bound ):
            super(MyEventCreator, self).__init__()
            self.lang_upper_bound = lang_upper_bound
            self.lang_lower_bound = lang_lower_bound
            self.lat_upper_bound  = lat_upper_bound
            self.lat_lower_bound  = lat_lower_bound
        
        def createObject(self, device, time):
            return {
                "time": time,
                "type": "MyEventType",
                "text": "Event Generated",
                "source": {
                    "id": device
                },
                "c8y_Position": {
                    'lng': random.uniform(self.lang_lower_bound, self.lang_upper_bound),
                    'lat': random.uniform(self.lat_lower_bound, self.lat_upper_bound)
                }
            }

Once the event creator class is defined, the test can start an event simulator process to generate events for specified devices with a specified rate per device by calling the ``startEventSimulator`` method. The test needs to pass the path to the Python file containing the event creator class, the name of the event creator class, and the values for the constructor parameters. 

For example, a test can use the above event creator class to generate position update events in the specified range:

.. code-block:: python

    # In the run.py file of the test
    class PySysTest(ApamaC8YPerfBaseTest):
        ...
        def execute(self):
            ...
            self.startEventSimulator(
                ['12345', '12346'],         # Device IDs
                1,                          # The rate of events to publish per device per second
                f'{self.input}/creator.py', # The Python file path containing the MyEventCreator class
                'MyEventCreator',           # The name of the event creator class
                [0.0, 10.0, 0.0. 10.0]      # The constructor parameters for the MyEventCreator class
            )
            ...

Sending alarms
--------------
A performance test that consumes alarms can either use real-time alarms from real devices or simulated alarms from simulated devices. To generate simulated alarms, the test can start alarm simulators to publish simulated alarms to Cumulocity at a specified rate which are then consumed by the EPL apps or smart rules being tested.

Different tests may have different requirements for the alarms being published. For example, a test may want to customize the type of alarms. To support such requirements, the framework requires tests to define an alarm creator class to create alarms of desired types. An alarm simulator uses an alarm creator object to create alarms to publish to Cumulocity.

The following example shows a test defining an alarm creator class to create alarms:

.. code-block:: python

    # In the 'creator.py' file in the test Input directory.
    import random
    from apamax.eplapplications.perf import ObjectCreator

    class MyAlarmsCreator(ObjectCreator):
        
        def createObject(self, device, time):
             return {
                    'source': {
                        'id': device
                    },
                    'type': 'my_alarm',
                    'text': 'My alarm',
                    'severity': 'MAJOR',
                    'status': 'ACTIVE',
                    'time': time,
                    }

Once the alarm creator class is defined, the test can start an alarm simulator process to generate alarms for specified devices with a specified rate per device by calling the ``startAlarmSimulator`` method. The test needs to pass the path to the Python file containing the alarm creator class, the name of the alarm creator class, and the values for the constructor parameters. 

For example, a test can use the above alarm creator class to generate alarms of MAJOR severity:

.. code-block:: python

    # In the run.py file of the test
    class PySysTest(ApamaC8YPerfBaseTest):
        ...
        def execute(self):
            ...
            self.startAlarmSimulator(
                ['12345', '12346'],         # Device IDs
                1,                          # The rate of alarms to publish per device per second
                f'{self.input}/creator.py', # The Python file path containing the MyAlarmsCreator class
                'MyAlarmsCreator',          # The name of the alarm creator class
                []                          # The constructor parameters for the MyAlarmsCreator class
            )
            ...

Monitoring the performance
---------------------------
The framework provides support for monitoring standard resource metrics of the Apama-ctrl microservice. The performance monitoring can be started by calling the ``startPerformanceMonitoring`` method.

The framework repeatedly collects the following raw resource metrics:

+ Aggregate physical memory usage of the microservice (combination of the memory used by the JVM helper and the Apama correlator process).
+ Aggregate CPU usage of the microservice in the most recent period.
+ Size of the correlator input queue.
+ Size of the correlator output queue.
+ The total number of events received by the correlator during the entire test.
+ The total number of events sent from the correlator during the entire test.

The CPU usage of the microservice is the total CPU usage of the whole container as reported by the OS for the cgroup of the entire container.

These metrics are then analyzed (mean, median, etc.) and used for graphing when the performance report is generated at the end of the test.

The test should wait for some time for performance metrics to be gathered before generating the performance report. It is a good practice to define the duration as a test option so that it can be configured easily when running a performance test.

Generating the performance reports
----------------------------------
Once the test has waited for the specified duration for the performance metrics to be collected, it must call the ``generateHTMLReport`` method to enable the generation of the performance report in the HTML format. The performance report (report.html) is generated at the end of the test in the test's output directory.

If the test is testing the same EPL app or smart rule with different configurations, then the ``generateHTMLReport`` method must be called at the end of each iteration. The performance report contains the result of each iteration.

Test configuration details can also be included in the report. The test should provide the values of all test options and test-controlled variables so that they are visible in the report.

In addition to the standard performance metrics, the HTML report can also contain additional performance metrics provided by the test, such as the number of alarms raised.

For example:

.. code-block:: python

    self.generateHTMLReport(
        description='Performance of MyExample app',
        # Test configurations and their values
        testConfigurationDetails={
            'Test duration (secs)': 30,
            'Measurement rate': 10,
        },
        # Extra performance metrics to include in the report.
        extraPerformanceMetrics={
            'Alarms raised': alarms_raised,
            'Alarms cleared': alarms_cleared,
        })

Writing a test for a multi-tenant microservice
===============================================
**Note:** EPL apps are currently not supported in multi-tenant microservices.

Writing a performance test for a multi-tenant microservice is similar to writing a test for a per-tenant microservice, with a few changes to handle multiple tenants.

The test can get a list of tenants subscribed to the multi-tenant Apama-ctrl microservice by calling the ``getSubscribedTenants`` method of the ``CumulocityPlatform`` object. Once the test has acquired the list of tenants to test, prepare each tenant and deploy smart rules to them by passing the tenant object to method calls. If simulated data is required, create simulated devices and start simulators for each tenant by passing the tenant object to method calls.

For example:

.. code-block:: python

    # Start performance monitoring
    perfMonitor = self.startPerformanceMonitoring()

    # Get subscribed tenants
    tenants = self.platform.getSubscribedTenants()

    # For each tenant, prepare it and deploy smart rule
    for tenant in tenants:
        # Prepare tenant
        self.prepareTenant(tenant=tenant)

        # Create SmartRulesManager for each tenant to deploy smart rules
        manager = SmartRulesManager(tenant, self.log)

        # Create smart rule
        rule = manager.build_onMeasurementExplicitThresholdCreateAlarm(...)
        # Deploy smart rule
        rule.deploy()

        if self.useSimulatedData:
            device = self.createTestDevice('my_device', tenant=tenant)
            self.startMeasurementSimulator(devices=[device], tenant=tenant, ...)

    # Wait for enough performance data to be gathered
    self.wait(self.testDuration)

    # Stop performance monitoring
    perfMonitor.stop()

See the OnExplicitThresholdCreateAlarm_MultiTenant sample in the smartrules-performance directory of the EPL Apps Tools SDK for a full example.

**Note:** In the case of multi-tenant microservices, the test framework assumes that the tenant configured in the pysysproject.xml file is an enterprise or management tenant which owns the microservice and is also subscribed to it along with some of its subtenants. It also assumes that the credentials configured in the pysysproject.xml file are valid for all subtenants. If different credentials are required for tenants, the test must create ``CumulocityTenant`` objects individually with the correct credentials.

Running the performance test
=============================
Performance tests can only be run using a Cumulocity tenant with EPL apps and smart rules enabled. Set up the framework to use a Cumulocity tenant by following the steps mentioned in `Testing in the Cumulocity cloud <using-pysys.rst#testing-in-the-cumulocity-cloud>`_.

When running a test, test options can be overridden by using the ``-X`` argument. See `Defining the test options`_ for details on defining and providing test options.

For example, to change the test duration of the ``AlarmOnThreshold`` test, run the following:

.. code-block:: shell
    
    pysys run -XtestDuration=180 AlarmOnThreshold

At the end of the test, a basic validation of the test run is performed. See `PySys helpers <https://cumulocity-iot.github.io/apama-eplapps-tools>`_ in the EPL Apps Tools documentation for details on validations performed.


Performance report
==================
At the end of a performance test, an HTML report is generated in the test's output directory. When running multiple iterations of the same EPL app or smart rules with different configurations, the results of each iteration are included in the report. The report contains metadata about the microservice and Cumulocity environment, test-specific configurations, performance summary, and graphs.

The report contains the following metadata about the microservice and the Cumulocity environment:

+ Cumulocity tenant URL
+ Cumulocity platform version
+ Apama-ctrl microservice name
+ Apama-ctrl microservice version (product code PAQ)
+ Apama platform version  (product code PAM)
+ Microservice resource limits

The report also contains test-specific configurations specified when calling the ``generateHTMLReport`` method. This usually contains all possible test-controlled variables.

The report contains min, max, mean, median, 75th percentile, 90th percentile, 95th percentile, and 99th percentile of the following standard performance metrics:

+ Total physical memory consumption of the microservice (MB)
+ JVM helper physical memory consumption (MB)
+ Apama correlator physical memory consumption (MB)
+ Correlator input queue size
+ Correlator output queue size
+ Correlator swap rate
+ Total CPU usage of the whole container (milliCPU)

Additionally, the report contains the following standard performance metrics and any extra performance metrics supplied by the test:

+ Total number of events received into the Apama correlator
+ Total number of events sent from the Apama correlator

The report also contains the following graphs over the duration of the test:

+ Correlator input queue and output queue size
+ Total microservice memory consumption, JVM helper memory consumption, and Apama correlator memory consumption
+ Microservice CPU usage

The summary of the various performance metrics and graphs provides an overview of how the microservice performed during the test run and how it varies for different configurations and workloads.

Sample EPL apps and tests
=========================
Multiple sample EPL apps and tests can be found in the samples-performance directory of the EPL Apps Tools SDK. The structure of the samples-performance directory is as follows:

| +--samples-performance
| +-----pysysdirconfig.xml
| +-----pysysproject.xml
| +-----apps/
| +-----correctness/
| +-----performance/

The apps directory contains multiple sample apps for performance testing. The correctness directory contains basic correctness tests of the sample apps. It is recommended to always test your EPL apps for correctness before testing them for performance. See `Using PySys to test your EPL apps <using-pysys.rst#using-pysys-to-test-your-epl-apps>`_ for details on testing EPL apps for correctness. The performance directory contains performance tests for each sample app. These tests can be run as explained in `Running the performance test`_.

Sample smart rule performance tests
===================================
Multiple sample smart rule performance tests can be found in the smartrules-performance directory of the EPL Apps Tools SDK. 

The tests can be run as explained in `Running the performance test`_.
