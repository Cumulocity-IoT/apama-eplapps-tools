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
from apama.basetest import ApamaBaseTest
from apamax.eplapplications import ApamaC8YBaseTest
from apama.correlator import CorrelatorHelper
import subprocess
import os 

class PySysTest(ApamaC8YBaseTest):

	def execute(self):
		
		# create a project with C8Y bundles
		project = self.createProject("c8y-basic")
		self.addC8YPropertiesToProject(project)
		
		# copy EPL app to be tested to the project's monitors dir
		self.copy(self.project.EPL_APPS+"/AlarmOnMeasurementThreshold.mon", project.monitorsDir()+"/AlarmOnMeasurementThreshold.mon")
		# copy EPL test file from Input dir to project's monitors dir 
		self.copy(self.input+"/AlarmOnMeasurementThresholdTest.mon", project.monitorsDir()+"/AlarmOnMeasurementThresholdTest.mon")
		
		project.deploy()

		# start local correlator
		correlator = CorrelatorHelper(self, name='c8y-correlator')
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())
		
		# wait for all events to be processed
		correlator.flush()
		
		# wait until the correlator gets a complete
		self.waitForGrep('c8y-correlator.log', expr="Removed monitor AlarmOnMeasurementThresholdTest")
		
	def validate(self):
		# look for log statements in the correlator log file
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)


