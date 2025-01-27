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
import os

class PySysTest(ApamaC8YPerfBaseTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XmeasurementFragment="a_frag" -XmeasurementSeries="a_series" TestName
		```
	"""
	# Restart the Apama microservice while preparing the tenant for running the performance test.
	restartMicroservice = False

	# The duration (in seconds) for the app to run for measuring the performance.
	testDuration = 300.0

	# If true, generate simulated data for performance testing with specified measurement type, fragment, and series.
	# If false, then the test does not generate any simulated data.
	useSimulatedData = True

	# The processing mode to use when publishing simulated measurements to Cumulocity IoT.
	cumulocityProcessingMode = 'CEP'

	##### Smartrule Configuration #####
	# The type of measurements, the app listens for.
	measurementType = 'type_device_temperature'

	# The type of the raised alarm.
	alarmType = 'DeviceTemperatureMonitoring'

	# The severity of the raised alarm.
	alarmSeverity = 'MAJOR'

	# The text of the raised alarm.
	alarmText = "Missing measurement for type #{type}"

	# Time (in minutes) to wait before raising missing measurement alarm
	timeInterval = 1.0

	##### Configurations for the simulators. #####
	# The number of devices to generate simulated data for.
	numDevices = 10

	# The number of the input measurements per second per device to generate.
	inputRatePerDevice = 1.0

	def execute(self):
		self.log.info(f'Testing onMeasurementMissingRaiseAlarm smartrule: useSimulatedData={self.useSimulatedData}, numDevices={self.numDevices},'
					  f' inputRatePerDevice={self.inputRatePerDevice}, testDuration={self.testDuration}')

		# Prepare the tenant for the test run.
		self.prepareTenant(restartMicroservice=self.restartMicroservice)

		# Start performance monitoring.
		perfMonitor = self.startPerformanceMonitoring()

		# Save the start time for querying generated alarms.
		self.startTime = self.getUTCTime()

		# Deploy the rule.
		rule = self.smartRulesManager.build_onMissingMeasurementsCreateAlarm(
			measurementType=self.measurementType,
			alarmType=self.alarmType,
			alarmSeverity=self.alarmSeverity,
			alarmText=self.alarmText,
			timeIntervalMinutes=self.timeInterval,
		)
		rule.deploy()

		# Create devices and start simulators if using simulated data.
		if self.useSimulatedData:
			# Create devices.
			devices = [self.createTestDevice(f'device{i + 1}') for i in range(self.numDevices)]

			# Enable rule only for these devices
			rule.setEnabledSources(devices)
			rule.deploy()

			# Start simulators.
			self.startSimulators(devices)

		# Wait for enough performance data to be gathered.
		self.wait(self.testDuration)
		
		# Stop performance monitoring.
		perfMonitor.stop()

		# Save the end time.
		self.endTime = self.getUTCTime()

		# Generate the HTML report.
		self.generateHTMLReport(f'onMissingMeasurementCreateAlarm smartrule with {self.numDevices} devices an input rate of {self.inputRatePerDevice} eps/device',
			testConfigurationDetails=self.getTestConfigurationDetails(), extraPerformanceMetrics=self.getExtraPerformanceMetrics())
	
	def startSimulators(self, devices):
		"""Start Measurement simulators for the sample app."""
		# Create one simulator process per device, unless testing for a large number of devices. 
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = min(10, self.numDevices)	# Create a maximum of 10 simulators.
		# Distribute the devices across simulators.
		simulatorsDevicesShare = [devices[i::simulatorCount] for i in range(simulatorCount)] # Devices split into simulatorCount parts.
		for simualatorDevices in simulatorsDevicesShare:
			self.startMeasurementSimulator(simualatorDevices, self.inputRatePerDevice, f'{self.input}/measurementCreator.py', 
						'MeasurementCreator', [self.measurementType, self.inputRatePerDevice, self.timeInterval],
										self.testDuration, processingMode=self.cumulocityProcessingMode)
			self.wait(1)

	def getTestConfigurationDetails(self):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Restart Apama MicroService': self.restartMicroservice,
			'Use simulated data': self.useSimulatedData,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Alarm type': self.alarmType,
			'Alarm severity': self.alarmSeverity,
			'Alarm text': self.alarmText,
			'Time interval (minutes)': self.timeInterval,
			'Number of devices': self.numDevices,
			'Input rate per device': self.inputRatePerDevice,
		}

	def getExtraPerformanceMetrics(self):
		"""
			Get count of alarms raised during test run.
		"""
		alarms = self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime)
		raised = 0
		for alarm in alarms:
			if 'count' in alarm:
				raised = raised + int(alarm['count'])
		
		return {
			'Alarms Raised': raised,
		}

	def validate(self):
		# Validate the test run and performance results.
		super(PySysTest, self).validate()
		
		# Report performance results
		if self.useSimulatedData:
			test_name = f'OnMissingMeasurementCreateAlarm smart rule with {self.numDevices} devices and {self.inputRatePerDevice} measurements per device'
		else:
			test_name = f'OnMissingMeasurementCreateAlarm smart rule with external input measurement streams'

		perf_stats = self.read_json('perf_statistics.json')
		self.reportPerformanceResult(perf_stats['correlator_iq_size']['mean'], f'{test_name} - mean correlator input queue size', PerformanceUnit('events', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['correlator_oq_size']['mean'], f'{test_name} - mean correlator output queue size', PerformanceUnit('events', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['total_memory_usage']['mean'], f'{test_name} - mean memory usage', PerformanceUnit('MB', biggerIsBetter=False))

