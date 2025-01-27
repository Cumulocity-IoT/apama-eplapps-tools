# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

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
import time
from datetime import datetime
import os

class PySysTest(ApamaC8YBaseTest):
	
	# The duration (in minutes) to wait for an Alarm to be cleared before creating an Operation.
	thresholdDuration = '0.25'
	
	# The type of the alarm to listen for.
	alarmType = 'test_type'

	# The fragment type for created operations.
	operationFragment = 'op_alarm_not_cleared'

	def execute(self):
		# Prepare the tenant for the test run.
		self.prepareTenant()

		# Configure the app by replacing placeholder values with the actual configured values
		appConfiguration = {
			'ALARM_CLEAR_DURATION_MINUTES': self.thresholdDuration,
			'ALARM_TYPE': self.alarmType,
			'OPERATION_FRAGMENT': self.operationFragment,
		}

		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'OperationOnAlarmNotCleared.mon'),
			os.path.join(self.output, 'OperationOnAlarmNotCleared.mon'), replacementDict=appConfiguration)
		self.copyWithReplace(os.path.join(self.input, 'OperationOnAlarmNotClearedTest.mon'),
			 os.path.join(self.output, 'OperationOnAlarmNotClearedTest.mon'), replacementDict=appConfiguration)

		eplapps = EPLApps(self.platform.getC8YConnection())

		# deploy the application
		eplapps.deploy(os.path.join(self.output, "OperationOnAlarmNotCleared.mon"), name='PYSYS_AppUnderTest', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AppUnderTest', errorExpr=['Error injecting monitorscript from file PYSYS_AppUnderTest'])

		eplapps.deploy(os.path.join(self.output, "OperationOnAlarmNotClearedTest.mon"), name='PYSYS_TestCase', redeploy=True, description='Test case, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_TestCase', errorExpr=['Error injecting monitorscript from file PYSYS_TestCase'])

		# delete apps at the end of test
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_AppUnderTest'))
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_TestCase'))

		self.waitForGrep(self.platform.getApamaLogFile(), expr="Removed monitor eplfiles.PYSYS_TestCase")

	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)
