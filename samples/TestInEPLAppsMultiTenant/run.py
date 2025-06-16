# Sample PySys testcase

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

	def execute(self):
		'''Fetch all subscribed tenants of the application'''
		self.tenants = self.platform.getSubscribedTenants()

		if len(self.tenants) < 0:
			self.log.warn("Please subscribe to the microservice before running test !! ")
			
		for tenant in self.tenants:
			# Prepare the tenant for the test run.
			self.prepareTenant(tenant=tenant)

		# Interacting with Apama EPL Apps in Cumulocity IoT
		eplapps = EPLApps(self.platform.getC8YConnection())

		# deploy the application
		eplapps.deploy(os.path.join(self.project.EPL_APPS, "AlarmOnMeasurementThresholdMultiTenant.mon"), name='PYSYS_AppUnderTest', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AppUnderTest', errorExpr=['Error injecting monitorscript from file PYSYS_AppUnderTest'])

		# deploy the test
		eplapps.deploy(os.path.join(self.input, 'AlarmOnMeasurementThresholdMultiTenantTest.mon'), name='PYSYS_TestCase', description='Test case, injected by test framework', redeploy=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_TestCase', errorExpr=['Error injecting monitorscript from file PYSYS_TestCase'])

		# Delete apps at the end of the test
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_TestCase'))
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_AppUnderTest'))

		# for each tenant and each case carries 2 test scenarios.
		# PAB-4293 fixed now.
		self.waitForGrep(self.platform.getApamaLogFile(),expr="Test Done !!",condition = f"=={len(self.tenants)*2}")
				
	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=r' (ERROR|FATAL) .* eplfiles\.', contains=False)
		




