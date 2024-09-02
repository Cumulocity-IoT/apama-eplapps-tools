# Sample PySys testcase

# Copyright (c) 2024 Software AG, Darmstadt, Germany and/or its licensors

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
import subprocess
import os 

class PySysTest(ApamaC8YBaseTest):

	def execute(self):
		 
		# create a project with C8Y bundles
		project = self.createProject("c8y-basic")
		self.addC8YPropertiesToProject(project)
		
		# copy sample EPL which generate an Alarm on threshold move
		self.copy(self.project.EPL_APPS+"/AlarmOnMeasurementThresholdMultiTenant.mon", project.monitorsDir()+"/AlarmOnMeasurementThresholdMultiTenant.mon")
		# copy EPL test file from Input dir to project's monitors dir 
		self.copy(self.input+"/AlarmOnMeasurementThresholdMultiTenantTest.mon", project.monitorsDir()+"/AlarmOnMeasurementThresholdMultiTenantTest.mon")
		
		project.deploy()

		# start local correlator
		correlator = CorrelatorHelper(self, name='c8y-correlator')
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())
		
		# wait for all events to be processed
		correlator.flush()
		
		# wait until the correlator gets a complete
		self.waitForGrep('c8y-correlator.log',expr="Test Done !!",condition = f"==2")

	def validate(self):
		# look for log statements in the correlator log file
		prefix = self.platform.getTenant().getTenantId() + " : "
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)
		self.assertGrep('c8y-correlator.log', expr=prefix + 'Received com.apama.cumulocity.Measurement.*myMeasurementType.*MeasurementValue\(110.*')
		self.assertGrep('c8y-correlator.log', expr=prefix + 'Received com.apama.cumulocity.Measurement.*myMeasurementType.*MeasurementValue\(90.*')
		self.assertGrep('c8y-correlator.log', expr=prefix + 'Received com.apama.cumulocity.Alarm.*ThresholdExceededAlarm.*Measurement value 110 exceeded threshold value 100.*"ACTIVE".*')
		self.assertGrep('c8y-correlator.log', expr=prefix + 'aboveThresholdTest: ThresholdExceededAlarm raised - PASS')
		self.assertGrep('c8y-correlator.log', expr=prefix + 'belowThresholdTest: ThresholdExceededAlarm not raised - PASS')