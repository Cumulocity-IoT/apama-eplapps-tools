# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from pysys.utils.perfreporter import PerformanceUnit
from apamax.eplapplications.perf.basetest import ApamaC8YPerfBaseTest
import json

class PySysTest(ApamaC8YPerfBaseTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		
	"""
	# Restart the Apama microservice while preparing the tenant for running the performance test.
	restartMicroservice = True

	# The duration (in seconds) for the app to run for measuring the performance.
	testDuration = 300.0

	# The processing mode to use when publishing simulated events to Cumulocity IoT.
	cumulocityProcessingMode = 'CEP'

	##### Smartrule Configuration #####
	# The type of the raised alarm.
	alarmType = 'DeviceTemperatureMonitoring'

	# The text of the raised alarm.
	alarmText = "Geofence alarm raised #{id}"

	# Geofence configuration. A json string of list of points.
	geofence = """[
					{"lng": 4.0, "lat": 1.0},
					{"lng": 4.0, "lat": 4.0},
					{"lng": 1.0, "lat": 4.0},
					{"lng": 1.0, "lat": 1.0}
				]"""
	# Trigger the smartrule on entry/exit/both.
	triggerAlarmOn = 'both'

	# List of the combinations to test.
	combinations = [
		# tuple of ('DeviceClassName', perDeviceRate, numOfDevices)
		('D', 0.1, [10, 50, 100, 500, 1000]),
		('E', 1, [10, 50, 100, 500, 1000])
	]

	def execute(self):
		for n, (deviceClassName, inputRatePerDevice, numOfDevicesList) in enumerate(self.combinations):
			for numOfDevices in numOfDevicesList:
				description = f'OnGeoferenceCreateAlarm smartrule with {numOfDevices} devices and input rate of {inputRatePerDevice} eps/device'

				self.log.info(f'Testing {description}')
				# Prepare the tenant for the test run.
				self.prepareTenant(restartMicroservice=self.restartMicroservice)

				# Start performance monitoring.
				perfMonitor = self.startPerformanceMonitoring()

				# Save the start time for querying generated alarms.
				self.startTime = self.getUTCTime()

				# Create devices.
				devices = [self.createTestDevice(f'device{i+1}') for i in range(numOfDevices)]

				# Deploy the rule
				geofence = json.loads(self.geofence)
				rule = self.smartRulesManager.build_onGeofenceCreateAlarm(
					geofence=geofence,
					alarmType=self.alarmType,
					alarmText=self.alarmText,
					triggerAlarmOn=self.triggerAlarmOn,
				)
				# Enable rule only for these devices
				rule.setEnabledSources(devices)
				rule.deploy()

				# Start simulators.
				self.startSimulators(devices, numOfDevices, inputRatePerDevice)

				# Wait for enough performance data to be gathered.
				self.wait(self.testDuration)
				
				# Stop performance monitoring.
				perfMonitor.stop()

				# Save the end time.
				self.endTime = self.getUTCTime()

				# Generate the HTML report.
				self.generateHTMLReport(description, testConfigurationDetails=self.getTestConfigurationDetails(numOfDevices, inputRatePerDevice),
					extraPerformanceMetrics=self.getExtraPerformanceMetrics())
			
	def startSimulators(self, devices, numDevices, inputRatePerDevice):
		"""Start Events simulators for the sample app."""
		# Create one simulator process per device, unless testing for a large number of devices. 
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = min(10, numDevices)	# Create a maximum of 10 simulators.
		# Distribute the devices across simulators.
		simulatorsDevicesShare = [devices[i::simulatorCount] for i in range(simulatorCount)] # Devices split into simulatorCount parts.
		for simualatorDevices in simulatorsDevicesShare:
			self.startEventSimulator(simualatorDevices, inputRatePerDevice, f'{self.input}/eventCreator.py', 
						'EventCreator', [inputRatePerDevice, numDevices, self.triggerAlarmOn], self.testDuration, processingMode=self.cumulocityProcessingMode)
			self.wait(1)

	def getTestConfigurationDetails(self, numDevices, inputRatePerDevice):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Restart Apama MicroService': self.restartMicroservice,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Alarm type': self.alarmType,
			'Alarm text': self.alarmText,
			'Number of devices': numDevices,
			'Input rate per device': inputRatePerDevice,
			'Trigger alarm on': self.triggerAlarmOn,
			'Geofence': self.geofence,
		}

	def getExtraPerformanceMetrics(self):
		"""
			Get count of alarms raised and alarms cleared during test run.
		"""
		alarms = self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime)
		raised = len(alarms)
		cleared = 0
		for alarm in alarms:
			if alarm.get('status', '') == 'CLEARED':
				cleared += 1
		
		return {
			'Alarms Raised': raised,
			'Alarms Cleared': cleared,
		}
