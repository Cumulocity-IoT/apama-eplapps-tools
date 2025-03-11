# Sample PySys testcase

# Copyright (c) 2020-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from apama.basetest import ApamaBaseTest
from apama.correlator import CorrelatorHelper
from apamax.eplapplications.basetest import ApamaC8YBaseTest

class PySysTest(ApamaC8YBaseTest):

	def execute(self):
		
		# create a project with C8Y bundles
		project = self.createProject("c8y-basic")
		self.addC8YPropertiesToProject(project)
			
		project.deploy()

		# start local correlator
		correlator = CorrelatorHelper(self, name='c8y-correlator')
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())

		self.waitForGrep('c8y-correlator.log', expr="Connected to Cumulocity IoT")
	
		# Inject our EPL files into the correlator.
		correlator.injectEPL([self.project.EPL_APPS+"/AlarmOnMeasurementThreshold.mon", self.input+"/AlarmOnMeasurementThresholdTest.mon"])
		
		
		# wait for all events to be processed
		correlator.flush()
		
		# wait until the correlator gets a complete
		self.waitForGrep('c8y-correlator.log', expr="Removed monitor AlarmOnMeasurementThresholdTest")
		
	def validate(self):
		# look for log statements in the correlator log file
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)


