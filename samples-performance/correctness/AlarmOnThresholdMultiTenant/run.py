# Copyright (c) 2022-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from apamax.eplapplications import EPLApps
from apamax.eplapplications.basetest import ApamaC8YBaseTest
import os

class PySysTest(ApamaC8YBaseTest):
	# The type of measurements, the app listens for.
	measurementType = 'my_measurement'
	# The measurement fragments, the app listens for.
	measurementFragment = 'my_fragment'
	# The measurement series, the app listens for.
	measurementSeries = 'my_series'
	# The measurement threshold value. An alarm is created if the measurement value is greater than this value.
	measurementThreshold = '100.0'
	# The type of the raised alarm.
	alarmType = 'ThresholdExceededAlarm'
	# The severity of the raised alarm.
	alarmSeverity = 'MINOR'

	def execute(self):

		self.tenants = self.platform.getSubscribedTenants()

		self.log.info(len(self.tenants))
		for tenant in self.tenants:
			# Prepare the tenant for the test run.
			self.prepareTenant(tenant=tenant)

		# Configure the app by replacing placeholder values with the actual configured values
		appConfiguration = {
			'MEASUREMENT_TYPE': self.measurementType,
			'MEASUREMENT_FRAGMENT': self.measurementFragment,
			'MEASUREMENT_SERIES': self.measurementSeries,
			'MEASUREMENT_THRESHOLD': self.measurementThreshold,
			'ALARM_TYPE': self.alarmType,
			'ALARM_SEVERITY': self.alarmSeverity,
		}
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'AlarmOnMeasurementThresholdMultiTenant.mon'),
			os.path.join(self.output, 'AlarmOnMeasurementThresholdMultiTenant.mon'), replacementDict=appConfiguration)
		self.copyWithReplace(os.path.join(self.input, 'AlarmOnThresholdMultiTenantTest.mon'),
			os.path.join(self.output, 'AlarmOnThresholdMultiTenantTest.mon'), replacementDict=appConfiguration)

		eplapps = EPLApps(self.platform.getC8YConnection())

		# Deploy the sample application
		eplapps.deploy(os.path.join(self.output, "AlarmOnMeasurementThresholdMultiTenant.mon"), name='PYSYS_AppUnderTest', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AppUnderTest', errorExpr=['Error injecting monitorscript from file PYSYS_AppUnderTest'])

		# Deploy the test application
		eplapps.deploy(os.path.join(self.output, 'AlarmOnThresholdMultiTenantTest.mon'), name='PYSYS_TestCase', description='Test case, injected by test framework', redeploy=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_TestCase', errorExpr=['Error injecting monitorscript from file PYSYS_TestCase'])

		# Delete apps at the end of the test
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_TestCase'))
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_AppUnderTest'))
		
		# for each tenant 2 test cases.
		self.waitForGrep(self.platform.getApamaLogFile(),expr="Test Done !!",condition = f"=={len(self.tenants)*2}")
		
		
	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)
		




