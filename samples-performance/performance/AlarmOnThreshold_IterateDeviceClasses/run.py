# Copyright (c) 2021 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from pysys.utils.perfreporter import PerformanceUnit
from apamax.eplapplications import EPLApps
from apamax.eplapplications.perf.basetest import EPLAppsPerfTest
import os, json

class PySysTest(EPLAppsPerfTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XmeasurementFragment="a_frag" -XmeasurementSeries="a_series" TestName
		```
	"""
	# Restart the Apama microservice while preparing the tenant for running the performance test.
	restartMicroservice = True
	
	# The duration (in seconds) for the app to run for measuring the performance for each variation.
	testDuration = 300.0

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
	
	# The approximate rate of total output alarms.
	approxTotalAlarmRate = 20

	# List of the combinations to test.
	combinations = [
		# tuple of ('DeviceClassName', perDeviceRate, numOfDevices)
		('D', 0.1, [10, 50, 100, 500, 1000]),
		('E', 1, [10, 50, 100, 500, 1000]),
		('F', 1000, [1, 2, 10]),
	]

	def execute(self):
		for n, (deviceClassName, inputRatePerDevice, numOfDevicesList) in enumerate(self.combinations):
			for numOfDevices in numOfDevicesList:
				description = f'{numOfDevices} Class {deviceClassName} devices (max {inputRatePerDevice} eps/device)'
				self.log.info(f'Testing {description}')
				
				# Prepare the tenant for the test run.
				self.prepareTenant(restartMicroservice=self.restartMicroservice)
				
				# Start performance monitoring.
				perfMonitor = self.startPerformanceMonitoring()

				# Save the start time for querying generated alarms.
				self.startTime = self.getUTCTime()

				# Deploy the sample app.
				self.deploySampleApp(n)

				# Create devices.
				devices = [self.createTestDevice(f'device{i+1}') for i in range(numOfDevices)]

				# Start simulators.
				self.startSimulators(devices, inputRatePerDevice)

				# Wait for enough performance data to be gathered.
				self.wait(self.testDuration)

				# Stop performance monitoring.
				perfMonitor.stop()
				
				# Save the end time.
				self.endTime = self.getUTCTime()

				# Generate the HTML report.
				self.generateHTMLReport(description, testConfigurationDetails=self.getTestConfigurationDetails(numOfDevices, inputRatePerDevice), 
					extraPerformanceMetrics=self.getExtraPerformanceMetrics())


	def deploySampleApp(self, count):
		"""Deploy the sample app."""

		# Configure the app by replacing the placeholder values with the actual configured values
		appConfiguration = {
			'MEASUREMENT_TYPE': self.measurementType,
			'MEASUREMENT_FRAGMENT': self.measurementFragment,
			'MEASUREMENT_SERIES': self.measurementSeries,
			'MEASUREMENT_THRESHOLD': self.measurementThreshold,
			'ALARM_TYPE': self.alarmType,
			'ALARM_SEVERITY': self.alarmSeverity,
		}
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'AlarmOnMeasurementThreshold.mon'), 
			os.path.join(self.output, 'AlarmOnMeasurementThreshold.mon'), replacementDict=appConfiguration, marker='@')
		
		# deploy the application
		self.eplapps.deploy(os.path.join(self.output, "AlarmOnMeasurementThreshold.mon"), name='PYSYS_AlarmOnMeasurementThreshold', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AlarmOnMeasurementThreshold', 
					condition=f'>{count}', errorExpr=['Error injecting monitorscript from file PYSYS_AlarmOnMeasurementThreshold'])


	def startSimulators(self, devices, inputRatePerDevice):
		"""Start Measurement simulators for the sample app."""
		numDevices = len(devices)
		# Create one simulator process per device, unless testing for a large number of devices. 
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = min(10, numDevices)	# Create a maximum of 10 simulators.
		# Distribute the devices across simulators.
		simulatorsDevicesShare = [devices[i::simulatorCount] for i in range(simulatorCount)] # Devices split into simulatorCount parts.

		# Configure the MeasurementCreator to generate values that result in an approximate target output alarm rate.
		# - The measurementCreator sends value from 0 to upperBound.
		# - The probability of getting a value greater than the threshold = (upperBound - threshold) / upperBound
		# - The probability should be equal to the target factional output alarm rate.

		alarmRateFraction = float(self.approxTotalAlarmRate) / float (numDevices * inputRatePerDevice)
		if alarmRateFraction > 0.5:
			#Simply generate 50% values greater than the threshold.
			upperValue = 2 * float(self.measurementThreshold)
		else:
			upperValue = float(self.measurementThreshold) / (1.0 - alarmRateFraction)

		for simualatorDevices in simulatorsDevicesShare:
			self.startMeasurementSimulator(simualatorDevices, inputRatePerDevice, f'{self.input}/measurementCreator.py', 
						'MeasurementCreator', [self.measurementType, self.measurementFragment, self.measurementSeries, upperValue], 
						self.testDuration, processingMode=self.cumulocityProcessingMode)


	def getTestConfigurationDetails(self, numDevices, inputRatePerDevice):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Restart Apama MicroService': self.restartMicroservice,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Measurement fragment': self.measurementFragment,
			'Measurement series': self.measurementSeries,
			'Measurement threshold': self.measurementThreshold,
			'Alarm type': self.alarmType,
			'Alarm severity': self.alarmSeverity,
			'Number of devices': numDevices,
			'Input rate per device': inputRatePerDevice,
			'Output alarm rate': self.approxTotalAlarmRate,
		}


	def getExtraPerformanceMetrics(self):
		""" Get count of alarms raised and alarms cleared during test run. """
		
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
