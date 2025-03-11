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
from pathlib import Path
import json, os, io, csv
from apamax.eplapplications import EPLApps


class PySysTest(ApamaC8YPerfBaseTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XmeasurementFragment="a_frag" -XmeasurementSeries="a_series" TestName
		```
	"""
	# The duration (in seconds) for the app to run for measuring the performance.
	testDuration = 60*30

	# If true, generate simulated data for performance testing with specified measurement type, fragment, and series.
	# If false, then the test does not generate any simulated data.
	useSimulatedData = True

	# The processing mode to use when publishing simulated measurements to Cumulocity IoT.
	cumulocityProcessingMode = 'CEP'

	# The type of measurements, the app listens for.
	measurementType = 'type_device_temperature'
    
    ##### Configurations for rule and eplapps. #####
	# The measurement fragments, the app listens for.
	measurementFragment = 'fragment_device_temperature'

	# The measurement series, the app listens for.
	measurementSeries = 'series_device_temperature'

	# The type of the raised alarm.
	alarmType = 'DeviceTemperatureMonitoring'
	eplAlarmType = 'ThresholdExceededAlarm'

	# The text of the raised alarm.
	alarmText = "Explicit threshold smartrule triggered for #{id}"

	# Range of values for which Alarm is generated
	rangeMin = 90
	rangeMax = 100

	##### Configurations for the simulators. #####
	# The number of rules to generate simulated data for.
	numRules = 5

	# The number of the input measurements per second per device to generate.
	inputRate = 1.0

	# The number of child tenants.
	numTenants = 50

	def execute(self):
		self.log.info(f'Testing Resource Consumption for multi-tenant microservice: useSimulatedData={self.useSimulatedData},'
					  f' inputRate={self.inputRate}, testDuration={self.testDuration}')
		# Getting parent tenant
		parentTenant = self.platform.getTenant()
		
		if self.mode == 'CloudMultiTenant':
			self.tenants = self.platform.getSubscribedTenants()
			if len(self.tenants) < self.numTenants + 1:
				self.log.warn( f"Please subscribe {self.numTenants} tenants before runnig test ... !")
				return
		else:
			self.tenants = [parentTenant]
   
		self.log.info(f"Total subscribed tenants {len(self.tenants)}")

		epl_app_names = self.createEplApp(parentTenant)
  
		self.requiredChildTenants = []
		tenantCount = 0
		if self.mode == 'CloudMultiTenant':
			for tenant in self.tenants:
				if parentTenant != tenant:
					self.requiredChildTenants.append(tenant)
					tenantCount +=1
				if tenantCount == self.numTenants:
					break				
		else:
			self.requiredChildTenants.append(parentTenant)
		self.log.info(f"Requested teants {len(self.requiredChildTenants)}")
		# Prepare the tenant for the test run.
		for tenant in self.requiredChildTenants:
			try:
				self.prepareTenant(tenant=tenant)
			except:
				self.log.info(f'Not able to prepare tenant id {tenant.id()}')

		self.tenantToDevices = {}
        # Create and deploy smart rule and device to tenants.
		self.log.info('Rule creation started....')
		for tenant in self.requiredChildTenants:
			smartRulesManager = SmartRulesManager(tenant,self.log)
			# Deploy the rule.
			devices=[]
			i = 0
			while i < self.numRules:
				i+=1
				rule = smartRulesManager.build_onMeasurementExplicitThresholdCreateAlarm(
					fragment=self.measurementFragment,
					series=self.measurementSeries,
					rangeMin=self.rangeMin,
					rangeMax=self.rangeMax,
					alarmType=self.alarmType,
					alarmText=str(tenant.getTenantId()) + "-" + str(i) + "-" + self.alarmText,
				)
				# Create devices.
				device = self.createTestDevice(f'device', tenant=tenant)
				devices.append(device)
				#Enable rule only for these devices
				rule.setEnabledSources(device)
				rule.deploy()
			self.tenantToDevices[tenant.getTenantId()] = devices
   
		self.wait(5)

		# Save the start time for querying generated alarms.
		self.startTime = self.getUTCTime()
		# Start performance monitoring.
		perfMonitor = self.startPerformanceMonitoring()

		# Start simulators.		
		for tenant in self.requiredChildTenants:
			self.log.info(f"startSimulator- {tenant.getTenantId()} devices {self.tenantToDevices[tenant.getTenantId()]}")
			self.target_alarm_rate = 1 / 60 #per sec
			requiredChildTenants = self.requiredChildTenants
			if len(requiredChildTenants) >= 50 and len(requiredChildTenants) < 100:
				self.target_alarm_rate = 0.5 / 60 #per sec
			elif len(requiredChildTenants) >= 100 and len(requiredChildTenants) < 200:
				self.target_alarm_rate = 0.25 / 60 #per sec
			elif len(requiredChildTenants) >= 200 and len(requiredChildTenants) < 500:
				self.target_alarm_rate = 0.125 / 60 #per sec
			elif len(requiredChildTenants) >= 500 and len(requiredChildTenants) < 1000:
				self.target_alarm_rate = 0.0625 / 60 #per sec
			elif len(requiredChildTenants) >= 1000:
				self.target_alarm_rate = 0.03125 / 60 #per sec
    
			self.startSimulator(self.tenantToDevices[tenant.getTenantId()], tenant)
		
		# Wait for enough performance data to be gathered.
		self.wait(self.testDuration)
		# Stop performance monitoring.
		perfMonitor.stop()
		# Save the end time.
		self.endTime = self.getUTCTime()
		# TODO - add clenaup
		self.deleteEplApp(tenant=parentTenant, epl_app_names=epl_app_names)
		# Generate the HTML report.
		self.generateHTMLReport(f'EPL MultiTenant Microservice (10 epl apps 5 rules) {self.inputRate} eps/device for {self.numTenants} tenants',
			testConfigurationDetails=self.getTestConfigurationDetails(), extraPerformanceMetrics=self.getExtraPerformanceMetrics())

	# Create epl to parent tenant
	def createEplApp(self, tenant):
		epl_app_names = []
		# Deploy the sample app.
		connection = tenant.getConnection()
		eplapps = EPLApps(connection)
		eplConfiguration = {
			'MEASUREMENT_TYPE': self.measurementType,
			'MEASUREMENT_FRAGMENT': self.measurementFragment,
			'MEASUREMENT_SERIES': self.measurementSeries,
		}
		self.copyWithReplace(os.path.join(self.input, 'thresholdAlarm.mon'), os.path.join(self.output, 'thresholdAlarm.mon'), replacementDict=eplConfiguration)

		for i in range(1, 11):
			eplapps.deploy(os.path.join(self.output, "thresholdAlarm.mon"), name="Test_EPL_APP"+ str(i), redeploy=True, description='Application under test, injected by test framework')
			self.waitForGrep(self.platform.getApamaLogFile(), expr=f'Added monitor eplfiles.Test_EPL_APP{str(i)}', errorExpr=[f'Error injecting monitorscript from file Test_EPL_APP{str(i)}'])
			epl_app_names.append("Test_EPL_APP"+ str(i))
		return epl_app_names

	# Delete epl to parent tenant
	def deleteEplApp(self, tenant, epl_app_names):
		connection = tenant.getConnection()
		eplapps = EPLApps(connection)
		for name in epl_app_names:
			eplapps.delete(name)

	def startSimulator(self, devices,tenant):
		"""Start Measurement simulators for the sample app."""
		self.startMeasurementSimulator(devices, self.inputRate, f'{self.input}/measurementCreator.py',
						'MeasurementCreator', [self.measurementType, self.measurementFragment, self.measurementSeries, self.rangeMin,
						self.rangeMax, self.inputRate, self.numRules, self.target_alarm_rate], self.testDuration, processingMode=self.cumulocityProcessingMode,tenant=tenant)

	def getTestConfigurationDetails(self):
		"""Get description of the test configurations to include in the report."""

		return {
			'Test duration (secs)': self.testDuration,
			'Use simulated data': self.useSimulatedData,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			'Measurement type': self.measurementType,
			'Measurement fragment': self.measurementFragment,
			'Measurement series': self.measurementSeries,
			'Alarm type': self.alarmType,
			'Alarm text': self.alarmText,
			'Range start': self.rangeMin,
			'Range end': self.rangeMax,
			'Number of devices': f'{self.numRules}',
			'Input rate per device': self.inputRate,
		}

	def getExtraPerformanceMetrics(self):
		"""
			Get count of alarms raised and alarms cleared during test run.
		"""
		alarms = []
		eplalarmsCount = 0
		tenantCount = 0
		for t in self.requiredChildTenants:
			#if tenantCount == self.numTenants + 1:
			#	break
			#tenantCount +=1
			alarms = alarms + self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime, connection=t.getConnection(), tenant=t)
			eplalarms = self.getAlarms(type=self.eplAlarmType, dateFrom=self.startTime, dateTo=self.endTime, connection=t.getConnection(), tenant=t)
			for alarm in eplalarms:
				eplalarmsCount += alarm.get('count', 0)
    
		self.log.info(f"alarms -> {len(alarms)}")
		self.log.info(f"eplalarmsCount -> {eplalarmsCount}")
  		
		raised = len(alarms) + eplalarmsCount  
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
			test_name = f'Explicit threshold 10 eplapps on parent tenant and 5 rules, each rule of one devices per child tenant with input rate of {self.inputRate} eps/device for {self.numTenants} child tenants'
		else:
			test_name = f'Explicit threshold 10 eplapps on parent tenant and 5 rules, each rule of one devices per child tenant with external input measurement streams for {self.numTenants} tenants'

		perf_stats = self.read_json('perf_statistics.json')
		self.reportPerformanceResult(perf_stats['total_memory_usage']['mean'], f'{test_name} - avg memory usage', PerformanceUnit('MB', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['total_memory_usage']['max'], f'{test_name} - max memory usage', PerformanceUnit('MB', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['cpu_usage_milli']['mean']/1000.0, f'{test_name} - avg cpu usage', PerformanceUnit('core', biggerIsBetter=False))
		self.reportPerformanceResult(perf_stats['cpu_usage_milli']['max']/1000.0, f'{test_name} - max cpu usage', PerformanceUnit('core', biggerIsBetter=False))