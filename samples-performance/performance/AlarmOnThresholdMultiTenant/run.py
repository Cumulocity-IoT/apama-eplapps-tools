# Copyright (c) 2022-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from pysys.utils.perfreporter import PerformanceUnit
from apamax.eplapplications.perf.basetest import EPLAppsPerfTest
from apamax.eplapplications.eplapps import EPLApps
import os

class PySysTest(EPLAppsPerfTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XmeasurementFragment="a_frag" -XmeasurementSeries="a_series" TestName
		```
	"""
	
	# The duration (in seconds) for the app to run for measuring the performance.
	testDuration = 300.0

	# If true, generate simulated data for performance testing with specified measurement type, fragment, and series. 
	# If false, then the test does not generate any simulated data.
	useSimulatedData = True

	# The processing mode to use when publishing simulated measurements to Cumulocity IoT.
	cumulocityProcessingMode = 'CEP'
	
	# The type of measurements, the app listens for.
	measurementType = 'my_measurement'
	
	# The measurement fragments, the app listens for.
	measurementFragment = 'my_fragment'
	
	# The measurement series, the app listens for.
	measurementSeries = 'my_series'
	
	# The measurement threshold value. An alarm is created if the measurement value is greater than this value.
	measurementThreshold = 100.0
	
	# The type of the raised alarm.
	alarmType = 'ThresholdExceededAlarm'
	
	# The severity of the raised alarm.
	alarmSeverity = 'MINOR'
	
	##### Configurations for simulator. #####
	# The number of devices to generate simulated data for.
	numDevices = 10

	#  The number of the input measurements per second per device to generate.
	inputRatePerDevice = 1.0

	# The approximate rate of total output alarms.
	approxTotalAlarmRate = 20

	def execute(self):
		self.log.info(f'Running test: useSimulatedData={self.useSimulatedData}, numDevices={self.numDevices}, inputRatePerDevice={self.inputRatePerDevice}, testDuration={self.testDuration}')
		
		self.tenants = self.platform.getSubscribedTenants()

		# Save the start time for querying generated alarms.
		self.startTime = self.getUTCTime()
		
		# Start performance monitoring.
		perfMonitor = self.startPerformanceMonitoring()

		# Prepare the tenant for the test run.
		self.prepareTenant()

		# Deploy the sample app.
		self.deploySampleApp()

		# Create devices and start simulators if using simulated data.
		if self.useSimulatedData:
			for tenant in self.tenants:
				# Create devices.
				devices = [self.createTestDevice(f'device{i+1}',tenant=tenant) for i in range(self.numDevices)]
				
				# Start simulators.
				self.startSimulators(devices,tenant)

		# Wait for enough performance data to be gathered.
		self.wait(self.testDuration)

		# Stop performance monitoring.
		perfMonitor.stop()

		# Save the end time.
		self.endTime = self.getUTCTime()

		# Generate the HTML report.
		self.generateHTMLReport(f'{self.numDevices} devices with input rate of {self.inputRatePerDevice} eps/device with {len(self.tenants)} tenants.', testConfigurationDetails=self.getTestConfigurationDetails(), 
					extraPerformanceMetrics=self.getExtraPerformanceMetrics())

	def deploySampleApp(self):

		# Configure the app by replacing the placeholder values with the actual configured values
		appConfiguration = {
			'MEASUREMENT_TYPE': self.measurementType,
			'MEASUREMENT_FRAGMENT': self.measurementFragment,
			'MEASUREMENT_SERIES': self.measurementSeries,
			'MEASUREMENT_THRESHOLD': self.measurementThreshold,
			'ALARM_TYPE': self.alarmType,
			'ALARM_SEVERITY': self.alarmSeverity,
		}
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'AlarmOnMeasurementThresholdMultiTenant.mon'), 
			os.path.join(self.output, 'AlarmOnMeasurementThresholdMultiTenant.mon'), replacementDict=appConfiguration, marker='@')
		
		# deploy the application
		self.eplapps.deploy(os.path.join(self.output, "AlarmOnMeasurementThresholdMultiTenant.mon"), name='PYSYS_AlarmOnMeasurementThresholdMultiTenant', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AlarmOnMeasurementThresholdMultiTenant', errorExpr=['Error injecting monitorscript from file PYSYS_AlarmOnMeasurementThreshold'])

	def startSimulators(self, devices,tenant):
		"""Start Measurement simulators for the sample app."""
		# Create one simulator process per device, unless testing for a large number of devices. 
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = min(10, self.numDevices)	# Create a maximum of 10 simulators.
		# Distribute the devices across simulators.
		simulatorsDevicesShare = [devices[i::simulatorCount] for i in range(simulatorCount)] # Devices split into simulatorCount parts.

		# Configure the MeasurementCreator to generate values that result in an approximate target output alarm rate.
		# - The measurementCreator sends value from 0 to upperBound.
		# - The probability of getting a value greater than the threshold = (upperBound - threshold) / upperBound
		# - The probability should be equal to the target factional output alarm rate.

		alarmRateFraction = float(self.approxTotalAlarmRate) / float (self.numDevices * self.inputRatePerDevice)
		if alarmRateFraction > 0.5:
			#Simply generate 50% values greater than the threshold.
			upperValue = 2 * float(self.measurementThreshold)
		else:
			upperValue = float(self.measurementThreshold) / (1.0 - alarmRateFraction)

		for simualatorDevices in simulatorsDevicesShare:
			self.startMeasurementSimulator(simualatorDevices, self.inputRatePerDevice, f'{self.input}/measurementCreator.py', 
						'MeasurementCreator', [self.measurementType, self.measurementFragment, self.measurementSeries, upperValue], 
						self.testDuration, processingMode=self.cumulocityProcessingMode,tenant=tenant)
	
	def getTestConfigurationDetails(self):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Use simulated data': self.useSimulatedData,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Measurement fragment': self.measurementFragment,
			'Measurement series': self.measurementSeries,
			'Measurement threshold': self.measurementThreshold,
			'Alarm type': self.alarmType,
			'Alarm severity': self.alarmSeverity,
			'Number of devices': self.numDevices,
			'Input rate per device': self.inputRatePerDevice,
			'Output alarm rate': self.approxTotalAlarmRate,
			'number of tenants': len(self.tenants),
		}

	def getExtraPerformanceMetrics(self):
		""" Get count of alarms raised and alarms cleared during test run. """
		alarms = []
		for tenant in self.tenants:
			alarms = self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime,connetion = tenant.getConnection())
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
		
		# Report performance results.
		if self.useSimulatedData:
			test_name = f'AlarmOnMeasurementThreshold using simulated data with {self.numDevices} devices, {self.inputRatePerDevice} ' + \
			f'measurements per device and threshold value {self.measurementThreshold}'
		else:
			test_name = f'AlarmOnMeasurementThreshold using external input measurement streams with threshold value {self.measurementThreshold}'
		
		perf_stats = self.read_json('perf_statistics.json')
		self.reportPerformanceResult(perf_stats['total_memory_usage']['mean'], f'{test_name} - mean memory usage', PerformanceUnit('MB', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['correlator_iq_size']['mean'], f'{test_name} - mean correlator input queue size', PerformanceUnit('events', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['correlator_oq_size']['mean'], f'{test_name} - mean correlator output queue size', PerformanceUnit('events', biggerIsBetter=False))
		