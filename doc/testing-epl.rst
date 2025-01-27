=====================================================
Writing tests for EPL apps
=====================================================
:Description: Guide to writing tests in EPL for your EPL apps. 

Introduction
=============

The behavior of most EPL apps usually consists of receiving data, sending measurements, and raising alarms. Thus to test that an EPL app produces the correct behavior will generally involve:

+ Creating device simulators.
+ Sending mock data to Cumulocity IoT.
+ Listening for events that the EPL app should produce.
+ Querying Cumulocity IoT for any objects created by the EPL app.

This can all be done using additional EPL apps that run parallel to the EPL app that we wish to test for correctness. This document will demonstrate some of the common processes involved in writing these additional EPL apps that test your existing EPL apps, while outlining some of the conventions for writing tests that best utilize the PySys test framework provided in the SDK. 

See the `Testing the performance of your EPL apps and smart rules <performance-testing.rst#testing-the-performance-of-your-epl-apps-and-smart-rules>`_ document for writing performance tests.

.. _device-simulator:

Creating device simulators
===========================
All measurements and alarms in Cumulocity IoT must be associated with a source. Devices in Cumulocity IoT are represented by managed objects, each of which has a unique identifier. When sending measurement or alarm events, the ``source`` field of these events must be set to a identifier of a managed object in Cumulocity IoT. Therefore, in order to send measurements from our test EPL app, it must create a ``ManagedObject`` device simulator to be the source of these measurements.

If you are using the PySys framework to `run tests in the cloud <using-pysys.rst#testing-in-the-cumulocity-iot-cloud>`_, any devices created by your tests should be named with prefix "PYSYS\_", and have the ``c8y_IsDevice`` property. These indicators are what the framework uses to identify which devices should be deleted following a test. Note that deleting a device in Cumulocity IoT will also delete any alarms or measurements associated with that device so the cleanup from a test is done when another test is next run. 

To see how this can be done, have a look at the ``createNewDevice`` action below::

	action createNewDevice(string name) returns integer 
	{
		ManagedObject mo := new ManagedObject;
		mo.type := DEVICE_TYPE;
		
		// Any devices with naming prefix "PYSYS_" and the c8y_IsDevice property 
		// will be cleaned from the tenant by the test framework  
		mo.name := "PYSYS_" + name; 
		mo.params.add("c8y_IsDevice", new dictionary<any, any>);

		// Create a ManagedObject in Cumulocity IoT and receive a response event confirming the change
		integer reqId := Util.generateReqId();
		send mo.withResponse(reqId, new dictionary<string, string>) to ManagedObject.SEND_CHANNEL;

		// Listener for when device has been created
		on ObjectCommitted(reqId=reqId) as resp
		 and not ObjectCommitFailed(reqId=reqId)
		{
			ManagedObject device := <ManagedObject> resp.object; 
			log "New simulator device created " + device.id at INFO;
			send DeviceCreated(device.id, reqId) to "TEST_CHANNEL";
		}
		// Listener for if creation of device fails
		on ObjectCommitFailed(reqId=reqId) as resp
		 and not ObjectCommitted(reqId=reqId)
		{
			log "Unable to create simulator device, reason : " + resp.toString() at ERROR;
			// Cause test to fail early, rather than wait for timeout
			die;
		}
		return reqId;
	}

This action initializes a ``ManagedObject`` (using the "PYSYS\_" naming prefix and adding the ``c8y_IsDevice`` property), before sending it using a ``withResponse`` action. It then confirms that it has been successfully created using listeners for ``ObjectCommitted`` and ``ObjectCommitFailed`` events. Whenever you are creating or updating an object in Cumulocity IoT and you want to verify that the change has been successful, it is recommended that you use the ``withResponse`` action in conjunction with ``ObjectCommitted`` and ``ObjectCommitFailed`` listeners (for more information, see the information on updating a managed object in the 'The Cumulocity IoT Transport Connectivity Plug-in' section of the `documentation <https://cumulocity.com/apama/docs/10.15/standard-connectivity-plugins/the-cumulocity-iot-transport-connectivity-plug-in/>`_). Using this approach you can easily relay when the process has completed (which is done by sending an event, ``DeviceCreated``, in the example above), and in the event of an error you can cause the test to exit quickly.


Sending events to your EPL apps
================================

If your EPL app listens for measurements (or any other kind of event), your test EPL app will need to send it some mock data, covering all edge cases we want to test, to verify that it responds correctly. Look at the ``sendMeasurement`` action defined below. It takes the identifier of a managed object (which is returned when we create a new device) and a measurement value as arguments::

	action sendMeasurement(string source, float value) returns integer
	{
		Measurement m := new Measurement;
		m.source := source;
		m.time := currentTime;
		m.type := MEASUREMENT_TYPE;
		m.measurements.getOrAddDefault(VALUE_FRAGMENT_TYPE).getOrAddDefault(VALUE_SERIES_TYPE).value := value;
		
		integer reqId := Util.generateReqId();
		send m.withResponse(reqId, new dictionary<string, string>) to Measurement.SEND_CHANNEL;

		// Listener for if creation of measurement fails
		on ObjectCommitFailed(reqId=reqId) as resp
		 and not ObjectCommitted(reqId=reqId) 
		{
			log "Unable to create measurement, reason : " + resp.toString() at ERROR;
			// Cause test to fail early, rather than wait for timeout
			die; 
		}

		log "Sending measurement with value " + value.toString() at INFO;
		return reqId;
	}

Similarly to the ``createNewDevice`` action, in this example we send the measurement using a ``withResponse`` action and define a ``ObjectCommitFailed`` listener, so that if there is an error creating the measurement in Cumulocity IoT we can cause the test to exit quickly instead of waiting for it to time out. 


Receiving events from your EPL apps
===================================

If your EPL app outputs events of any kind, your test app will need to listen for those events to verify that the expected events are being produced. Your tests should construct listeners for both possibilites: one for if an event *is* produced by the EPL app being tested; and another for if an event is *not* produced. 

Below is a section of a test that listens for an alarm event after a measurement is sent to Cumulocity IoT:: 

	on DeviceCreated(reqId=createNewDevice("DeviceSimulator")) as device 
	{
		// Send measurement and check to see whether an alarm is raised 
		monitor.subscribe(Alarm.SUBSCRIBE_CHANNEL);
		integer measurementReqId := sendMeasurement(device.deviceId, value);
		
		// Listener for if alarm is raised within timeout
		on Alarm(source=device.deviceId, type=ALARM_TYPE) 
		 and not wait(ALARM_WAIT_TIMEOUT) 
		{
			if expectingAlarm {
				log ALARM_TYPE + " raised - PASS" at INFO;
			} else {
				log ALARM_TYPE + " raised when none was expected - FAIL" at ERROR;
			}
		}
		// Listener for if alarm is not raised within timeout
		on wait(ALARM_WAIT_TIMEOUT) 
		 and not Alarm(source=device.deviceId, type=ALARM_TYPE) 
		{
			if expectingAlarm {
				log ALARM_TYPE + " not raised when one was expected - FAIL" at ERROR;
			} else {
				log ALARM_TYPE + " not raised - PASS" at INFO;
			}
		}
	}

To receive the alarm event, firstly we must subscribe to the relevant channel, ``Alarm.SUBSCRIBE_CHANNEL``. We then constuct two listeners, one for each possible outcome: the first is for if an alarm *is* raised by the measurement; and the second listens for if an alarm event is *not* raised (within a defined timeout period). 

Querying Cumulocity IoT
========================

An alternative approach to the one demonstrated in the '`Receiving events from your EPL apps`_' section involves querying Cumulocity IoT. With this approach you are able to retrieve historical data. It is possible to query Cumulocity IoT for alarms, events, measurements, operations, and managed objects. More information on querying can be found in 'The Cumulocity IoT Transport Connectivity Plug-in' section of the  `documentation <https://cumulocity.com/apama/docs/10.15/standard-connectivity-plugins/the-cumulocity-iot-transport-connectivity-plug-in/>`_.

Using an example of a test that checks for an alarm, this would involve subscribing to the ``FindAlarmResponse.SUBSCRIBE_CHANNEL`` and using a ``FindAlarm`` event with ``FindAlarmResponse`` and ``FindAlarmResponseAck`` listeners::

	on DeviceCreated(reqId=createNewDevice("DeviceSimulator")) as device 
	{
		monitor.subscribe(FindAlarmResponse.SUBSCRIBE_CHANNEL);        
		integer reqId := Util.generateReqId();

		// Send measurement and check to see whether an alarm is raised 
		integer measurementReqId := sendMeasurement(device.deviceId, value);
		on ObjectCommitted(reqId=measurementReqId)
		and not ObjectCommitFailed(reqId=measurementReqId)
		{
			send FindAlarm(reqId, {"source": device.deviceId, "type": ALARM_TYPE, "resolved": "false"}) to FindAlarm.SEND_CHANNEL;
		}
			
		// Listener for if alarm has been raised
		on FindAlarmResponse(reqId=reqId) and not FindAlarmResponseAck(reqId=reqId) {
			if expectingAlarm {
				log ALARM_TYPE + " raised - PASS" at INFO;
			} else {
				log ALARM_TYPE + " raised when none was expected - FAIL" at ERROR;
			}
		}
		// Listener for if alarm has not been raised
		on FindAlarmResponseAck(reqId=reqId) and not FindAlarmResponse(reqId=reqId){
			if expectingAlarm {
				log ALARM_TYPE + " not raised when one was expected - FAIL" at ERROR;
			} else {
				log ALARM_TYPE + " not raised - PASS" at INFO;
			}
		}
	}

Note that with this approach you will need to ensure that the ``FindAlarm`` event is sent after the alarm has appeared in Cumulocity IoT. 
 

Reporting test outcomes 
========================

As a general rule, messages from a passing test should be logged at ``INFO``, and messages from a failure should be logged at ``ERROR``. Look at the EPL snippets in the '`Receiving events from your EPL apps`_' and '`Querying Cumulocity IoT`_' sections to see examples of how the test outcome should be reported. Any messages logged at ``ERROR`` will automatically raise a MAJOR alarm in Cumulocity IoT, alerting you to the test failure. You will need to use this convention of logging failures at ``ERROR`` if you are using the PySys framework to run your tests, as the framework determines whether a test has passed or failed based on whether there are any messages logged at ``ERROR`` (or ``FATAL``) in the correlator log after the test has completed. 
 

Exiting the test
=================
The test framework will wait until all test cases have terminated before completing. It's important to either have your test explicitly ``die``, or arrange that when your test finishes all listeners have terminated, since this will also cause your test case to exit. In the EPL examples above, notice how if an unexpected error occurs (for example, if sending a measurement or creating a device fails), then the ``die`` statement is used to exit the test early, rather than waiting for it to time out. If your test has defined any listeners for multiple events using the ``on all`` operator, then you will need to include a ``die`` statement after the test code has been executed. 


Summary
=========

+ EPL apps can be tested using other EPL apps that run alongside the app being tested for correctness. 
+ If your test needs to send measurements or raise alarms, use managed objects to create device simulators to act as the source. If using the PySys framework to test your EPL apps in the cloud, prefix your device ``name`` with "PYSYS\_" and add ``c8y_IsDevice`` to the managed object's ``params`` for the framework to clean up devices created by the test.
+ If your EPL app receives input data, your test should send it some mock data (covering all edge cases) to see that it responds correctly. 
+ If your EPL app produces output events, use listeners for those events or query Cumulocity IoT in your test EPL apps to verify the output.  
+ Log test passes at ``INFO`` and test failures at ``ERROR``.
+ Make sure there are no active listeners in your tests when they have finished executing.          


EPL test samples
-----------------
A sample EPL app and test can be found in the samples directory of the EPL Apps Tools SDK. Most of the EPL code snippets in this document are from the sample test, AlarmOnMeasurementThresholdTest, which can be found in the Input directory of any of the samples provided. This tests the sample EPL app, AlarmOnMeasurementThreshold, which can be found in the samples/apps directory of the SDK. Information on how to run the sample test can be found in the `Using PySys to test your EPL apps <using-pysys.rst#using-pysys-to-test-your-epl-apps>`_ document.



