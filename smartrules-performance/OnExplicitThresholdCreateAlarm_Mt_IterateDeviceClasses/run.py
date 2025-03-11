# Copyright (c) 2023-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

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
from apamax.eplapplications.smartrules import SmartRulesManager
import concurrent.futures
import json, time, urllib

class PySysTest(ApamaC8YPerfBaseTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XmeasurementFragment="a_frag" -XmeasurementSeries="a_series" TestName
		```
	"""
	# The duration (in seconds) for the app to run for measuring the performance.
	testDuration = 1800.0

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

	# The number of tenants to test against.
	numOfTenants = 10

	# List of the combinations to test.
	combinations = [
		# tuple of ('DeviceClassName', inputRatePerDevice, numOfDevices)
		('C', 0.01, [10, 100, 1000]),
		('D', 0.1, [10, 100, 1000]),
		('E', 1, [10, 100]),
		('F', 1000, [1, 10])
	]

	def execute(self):
		
		self.ThreadCount = self.numOfTenants/10
		self.posThreadIdMap = {}
		self.tenants = self.platform.getSubscribedTenants()
		
		if len(self.tenants) < self.numOfTenants:
			self.log.warn( f"Please subscribe {self.numOfTenants} tenants before runnig test ... !")
			return
		
		tenantToClassMap = {
			1: ["C", "D", "E", "F"],
			10: ["C", "D", "E"],
			100: ["C", "D"],
			1000: ["C"]
		}
		self.classesToTest = []
		for tenantNum in tenantToClassMap:
			if self.numOfTenants <= tenantNum:
				self.classesToTest = tenantToClassMap[tenantNum]
				break
		
		self.tenantsToTest = self.tenants[:self.numOfTenants]

		for n, (deviceClassName, inputRatePerDevice, numOfDevicesList) in enumerate(self.combinations):
			if not deviceClassName in self.classesToTest: continue
			
			for numDevices in numOfDevicesList:	 # [10,	 100,  1000, 10000]
				
				self.numOfMsmtBtwAlrm = numDevices * inputRatePerDevice * self.numOfTenants * 10

				description = f'10 explicit threshold smartrules with {numDevices} devices per tenant and input rate of {inputRatePerDevice} eps/device and noOftenants = {self.numOfTenants}'
				self.log.info(f'Testing {description}')
				
				self.tenantToDevices = {}
				self.threadIDPos = {}

				self.log.info("Cleaning all tenants")
				self._prepareTenant()
				self.log.info("Cleaned all tenants")

				tenants_finished =0
				# Iterate over the tenants list and deploy 10 smart rules on each tenant. 
				for tenant in self.tenantsToTest:
					# general logging to make sure the number of tenants got completed.
					tenants_finished = tenants_finished +1
					if tenants_finished == 100:
						self.log.info(f"Completed deploying rules on {tenants_finished} tenants")
						tenants_finished = 0
					if tenants_finished < 2:
						self.log.info(f"deploying rules on tenants!! ")
					

					# create smartrule manager instance.
					smartRulesManager = SmartRulesManager(tenant, self.log)

					# Deploy the rules.
					rules = []
					for i in range(1, 11):
						rules.append(
							smartRulesManager.build_onMeasurementExplicitThresholdCreateAlarm(
								fragment=self.measurementFragment,
								series=self.measurementSeries,
								rangeMin=self.rangeMin,
								rangeMax=self.rangeMax,
								alarmType=self.alarmType,
								alarmText=str(tenant.getTenantId()) + "-" + str(i) + "-" + self.alarmText,
							)
						)

					# Create devices.
					devices = [self.createTestDevice(f'device{i + 1}', tenant=tenant) for i in range(numDevices)]
					self.tenantToDevices[tenant.getTenantId()] = devices
					
					# deploy rules
					for rule in rules:
						# Enable rule only for these devices
						rule.setEnabledSources(devices)
						rule.deploy()
					
				# Save the start time for querying generated alarms.
				self.startTime = self.getUTCTime()

				# Start performance monitoring.
				perfMonitor = self.startPerformanceMonitoring()
				
				# Send initial measurement to each device if number of tenants are more.
				# This is to reduce load  on core. 
				if self.numOfTenants >= 100:
					self.sendInitialMeasurement()
				
				for tenant in self.tenantsToTest:
					# Start simulators.
					self.startSimulator(self.tenantToDevices[tenant.getTenantId()], tenant, numDevices, inputRatePerDevice)
				
				# Wait for enough performance data to be gathered.
				self.wait(self.testDuration)

				# Stop performance monitoring.
				perfMonitor.stop()

				# Stop any running simulators
				self._stopSimulators(tenant.getTenantId())

				# Save the end time.
				self.endTime = self.getUTCTime()

				# Generate the HTML report.
				self.generateHTMLReport(
					f'Explicit threshold for {numDevices} devices per tenant with input rate of {inputRatePerDevice} eps/device for {self.numOfTenants} tenants',
					testConfigurationDetails=self.getTestConfigurationDetails(numDevices, inputRatePerDevice,
																				self.numOfTenants),
					extraPerformanceMetrics=self.getExtraPerformanceMetrics())

				
	def sendInitialMeasurement(self):
		"""Send one measurement to the device. """
		self.log.info(f"Sending initial measurement to all devices on each tenant" )
		
		TENANTS_BATCH = 50 
		# Make tenants as batch of TENANTS_BATCH number of tenants in rach batch
		tenantsBatch = [self.tenantsToTest[x:x+TENANTS_BATCH] for x in range(0, len(self.tenantsToTest), TENANTS_BATCH)]
		# Send initial measurements to each batch
		for tenantList in tenantsBatch:
			self.log.info(f"Sending initial measurement to all devices on each tenant {len(tenantList)}" )
			for tenant in tenantList:
				batch = []
				for dev in self.tenantToDevices[tenant.getTenantId()]:
					batch.append({'time': self.getUTCTime(), "type": self.measurementType,
									"source": {"id": dev},
									self.measurementFragment: {self.measurementSeries: {"value": 10.0 , "unit": "mm"}}})
				
				self.do_send(json.dumps({"measurements": batch}), tenant)
			self.wait(30)
	
	def do_send(self, body,tenant):
		"""Send event(s) to Cumulocity IOT."""
		headers = {
					'Content-Type': 'application/vnd.com.nsn.cumulocity.measurementcollection+json',
					'X-Cumulocity-Processing-Mode': self.cumulocityProcessingMode
				}
		startTime = time.time()
		MAX_RETRY_TIME = 60.0
		while time.time() < startTime + MAX_RETRY_TIME:
			try:
				tenant.getConnection().request('POST', '/measurement/measurements', body,headers=headers)
				return
			except urllib.error.HTTPError as ex:
				# Retry in case of 5XX error.
				if ex.code // 100 == 5:
					time.sleep(0.5)
				self.log.warn(f'WARN: Failed to send to Cumulocity IoT, retrying; error={ex}')
		
	def _prepareTenant(self):
		''' Cleaning tenants in parallel '''
		def parallelly_prepareTenant(self, tenantList):
			# Prepare the tenant for the test run.
			for tenant in tenantList:
				self.prepareTenant(tenant=tenant)
			self.log.info("Completed Thread !!")
		
		# Create configured number of threads and clean the tenants parallelly
		with concurrent.futures.ThreadPoolExecutor(max_workers=self.ThreadCount) as executor:
			tenantsInEachBatch = int(len(self.tenantsToTest) / self.ThreadCount)
			# Make the tenants into batches bases on the thread count.
			tenantsBatch = [self.tenantsToTest[x:x+tenantsInEachBatch] for x in range(0, len(self.tenantsToTest), tenantsInEachBatch)]
			try:
				threads = []
				for tenantList in enumerate(tenantsBatch):
					threads.append(executor.submit(parallelly_prepareTenant,self,tenantList))
						
				concurrent.futures.wait(threads)
			except Exception as err:
				self.log.error(f"Exception while cleaning tenant: {err}" )
				pass
			
	def startSimulator(self, devices, tenant, numDevices, inputRatePerDevice):
		"""Start Measurement simulators for the sample app."""
		# Create one simulator process per device, unless testing for a large number of devices and tenants.
		# Let a simulator process handle multiple devices if testing for a large number of devices.
		simulatorCount = 1
		simulatorsDevicesShare = [devices]
		# As high rate of data we can use more threads
		if self.numOfTenants < 10: 
			simulatorCount = min(10, numDevices)  # Create a maximum of 10 simulators.
			# Distribute the devices across simulators.
			simulatorsDevicesShare = [devices[i::simulatorCount] for i in
										range(simulatorCount)]	# Devices split into simulatorCount parts.
		for simulatorDevices in simulatorsDevicesShare:
			self.startMeasurementSimulator(simulatorDevices, inputRatePerDevice, f'{self.input}/measurementCreator.py',
											'MeasurementCreator',
											[self.measurementType, self.measurementFragment, self.measurementSeries,
											self.rangeMin,
											self.rangeMax, inputRatePerDevice, numDevices,self.numOfMsmtBtwAlrm], self.testDuration,
											processingMode=self.cumulocityProcessingMode, tenant=tenant)

	def getTestConfigurationDetails(self, numDevices, inputRatePerDevice, numTenants):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Measurement fragment': self.measurementFragment,
			'Measurement series': self.measurementSeries,
			'Alarm type': self.alarmType,
			'Alarm text': self.alarmText,
			'Range start': self.rangeMin,
			'Range end': self.rangeMax,
			'Number of devices': numDevices,
			'Input rate per device': inputRatePerDevice,
			'Number of tenants': numTenants,
		}

	def getExtraPerformanceMetrics(self):
		"""
			Get count of alarms raised and alarms cleared during test run.
		"""
		alarms = []
		for t in self.tenantsToTest:
			alarms = alarms + self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime,
												connection=t.getConnection())
		raised = len(alarms)
		cleared = 0
		for alarm in alarms:
			if alarm.get('status', '') == 'CLEARED':
				cleared += 1

		return {
			'Alarms Raised': raised,
			'Alarms Cleared': cleared,
		}