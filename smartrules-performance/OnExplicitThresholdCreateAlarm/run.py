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

	# The type of measurements, the app listens for.
	measurementType = 'type_device_temperature'

	##### Smart rule Configuration #####
	# The measurement fragments, the app listens for.
	measurementFragment = 'fragment_device_temperature'

	# The measurement series, the app listens for.
	measurementSeries = 'series_device_temperature'

	# The type of the raised alarm.
	alarmType = 'DeviceTemperatureMonitoring'

	# The text of the raised alarm.
	alarmText = "Explicit threshold smartrule triggered for #{id}"

	# Range of values for which Alarm is generated
	rangeMin = 50
	rangeMax = 100

	##### Configurations for the simulators. #####
	# The number of devices to generate simulated data for.
	numDevices = 10

	# The number of the input measurements per second per device to generate.
	inputRatePerDevice = 1.0

	def execute(self):
		self.log.info(f'Testing explicitThreshold smart rule: useSimulatedData={self.useSimulatedData}, numDevices={self.numDevices},'
					  f' inputRatePerDevice={self.inputRatePerDevice}, testDuration={self.testDuration}')

		# Prepare the tenant for the test run.
		self.prepareTenant(restartMicroservice=self.restartMicroservice)

		# Start performance monitoring.
		perfMonitor = self.startPerformanceMonitoring()

		# Save the start time for querying generated alarms.
		self.startTime = self.getUTCTime()

		# Deploy the rule.
		rule = self.smartRulesManager.build_onMeasurementExplicitThresholdCreateAlarm(
			fragment=self.measurementFragment,
			series=self.measurementSeries,
			rangeMin=self.rangeMin,
			rangeMax=self.rangeMax,
			alarmType=self.alarmType,
			alarmText=self.alarmText,
		)
		rule.deploy()

		# Create devices and start simulators if using simulated data.
		if self.useSimulatedData:
			# Create devices.
			devices = [self.createTestDevice(f'device{i+1}') for i in range(self.numDevices)]

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
		self.generateHTMLReport(f'explicit threshold {self.numDevices} devices with input rate of {self.inputRatePerDevice} eps/device',
			testConfigurationDetails=self.getTestConfigurationDetails(), extraPerformanceMetrics=self.getExtraPerformanceMetrics())
	
	def startSimulators(self, devices):
		"""Start Measurement simulators for the sample app."""
		# Create one simulator process per device, unless testing for a large number of devices. 
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = min(10, self.numDevices)	# Create a maximum of 10 simulators.
		# Distribute the devices across simulators.
		simulatorsDevicesShare = [devices[i::simulatorCount] for i in range(simulatorCount)] # Devices split into simulatorCount parts.
		for simulatorDevices in simulatorsDevicesShare:
			self.startMeasurementSimulator(simulatorDevices, self.inputRatePerDevice, f'{self.input}/measurementCreator.py',
						'MeasurementCreator', [self.measurementType, self.measurementFragment, self.measurementSeries, self.rangeMin,
						self.rangeMax, self.inputRatePerDevice, self.numDevices], self.testDuration, processingMode=self.cumulocityProcessingMode)
			self.wait(1)

	def getTestConfigurationDetails(self):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Restart Apama MicroService': self.restartMicroservice,
			'Use simulated data': self.useSimulatedData,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Measurement fragment': self.measurementFragment,
			'Measurement series': self.measurementSeries,
			'Alarm type': self.alarmType,
			'Alarm text': self.alarmText,
			'Range start': self.rangeMin,
			'Range end': self.rangeMax,
			'Number of devices': self.numDevices,
			'Input rate per device': self.inputRatePerDevice,
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

	def validate(self):
		# Validate the test run and performance results.
		super(PySysTest, self).validate()
		
		# Report performance results
		if self.useSimulatedData:
			test_name = f'Explicit threshold smart rule with {self.numDevices} devices and {self.inputRatePerDevice} measurements per device'
		else:
			test_name = f'Explicit threshold smart rule with external input measurement streams'

		perf_stats = self.read_json('perf_statistics.json')
		self.reportPerformanceResult(perf_stats['correlator_iq_size']['mean'], f'{test_name} - mean correlator input queue size', PerformanceUnit('events', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['correlator_oq_size']['mean'], f'{test_name} - mean correlator output queue size', PerformanceUnit('events', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['total_memory_usage']['mean'], f'{test_name} - mean memory usage', PerformanceUnit('MB', biggerIsBetter=False))

