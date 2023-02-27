# Sample PySys testcase

# Copyright (c) 2020 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from apamax.eplapplications import CumulocityPlatform, EPLApps
from apamax.eplapplications.basetest import ApamaC8YBaseTest
import os 

class PySysTest(ApamaC8YBaseTest):

	def execute(self):

		# connect to the platform
		self.platform = CumulocityPlatform(self)
		eplapps = EPLApps(self.platform.getC8YConnection())

		# deploy the application
		eplapps.deploy(os.path.join(self.project.EPL_APPS, "AlarmOnMeasurementThreshold.mon"), name='PYSYS_AppUnderTest', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AppUnderTest', errorExpr=['Error injecting monitorscript from file PYSYS_AppUnderTest'])

		# deploy the test
		eplapps.deploy(os.path.join(self.input, 'AlarmOnMeasurementThresholdTest.mon'), name='PYSYS_TestCase', description='Test case, injected by test framework', redeploy=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_TestCase', errorExpr=['Error injecting monitorscript from file PYSYS_TestCase'])

		# wait until the test completes
		self.waitForGrep(self.platform.getApamaLogFile(), expr="Removed monitor eplfiles.PYSYS_TestCase")
		
	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)
		




