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
import os

class PySysTest(ApamaC8YBaseTest):
	# The type of measurements, the app listens for.
	measurementType = 'my_measurement'
	# The measurement fragments, the app listens for.
	measurementFragment = 'my_fragment'
	# The measurement series, the app listens for.
	measurementSeries = 'my_series'
	# The type of the raised alarm.
	alarmType = 'DeviceAverageBeyondRange'
	# The severity of the raised alarm.
	alarmSeverity = 'MINOR'
	# The window duration (in seconds) for the moving average.
	windowDurationSecs = 60

	def execute(self):
		# Prepare the tenant for the test run.
		self.prepareTenant()

		# Configure the app by replacing the placeholder values with the actual configured values
		appConfiguration = {
			'MEASUREMENT_TYPE': self.measurementType,
			'MEASUREMENT_FRAGMENT': self.measurementFragment,
			'MEASUREMENT_SERIES': self.measurementSeries,
			'ALARM_TYPE': self.alarmType,
			'ALARM_SEVERITY': self.alarmSeverity,
			'WINDOW_DURATION_SECS': self.windowDurationSecs,
		}
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'AlarmOnAbnormalMeanDeviation.mon'),
			os.path.join(self.output, 'AlarmOnAbnormalMeanDeviation.mon'), replacementDict=appConfiguration)
		self.copyWithReplace(os.path.join(self.input, 'AlarmOnAbnormalMeanDeviationTest.mon'),
			os.path.join(self.output, 'AlarmOnAbnormalMeanDeviationTest.mon'), replacementDict=appConfiguration)

		eplapps = EPLApps(self.platform.getC8YConnection())

		# Deploy the sample app
		eplapps.deploy(os.path.join(self.output, "AlarmOnAbnormalMeanDeviation.mon"), name='PYSYS_AlarmOnAbnormalMeanDeviation', redeploy=True, description='Application under test, injected by test framework')
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AlarmOnAbnormalMeanDeviation', errorExpr=['Error injecting monitorscript from file PYSYS_AlarmOnAbnormalMeanDeviation'])

		# Deploy the test app
		eplapps.deploy(os.path.join(self.output, 'AlarmOnAbnormalMeanDeviationTest.mon'), name='PYSYS_AlarmOnAbnormalMeanDeviationTestCase', description='Test case, injected by test framework', redeploy=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.PYSYS_AlarmOnAbnormalMeanDeviationTestCase', errorExpr=['Error injecting monitorscript from file PYSYS_AlarmOnAbnormalMeanDeviationTestCase'])
		
		# delete apps at the end of test
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_AlarmOnAbnormalMeanDeviationTestCase'))
		self.addCleanupFunction(lambda: eplapps.delete('PYSYS_AlarmOnAbnormalMeanDeviation'))
		# wait until the test completes
		self.waitForGrep(self.platform.getApamaLogFile(), expr="Removed monitor eplfiles.PYSYS_AlarmOnAbnormalMeanDeviationTestCase")
	
	def validate(self):
		# check none of the tests failed
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)
		




