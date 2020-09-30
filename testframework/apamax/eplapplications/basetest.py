## License
# Copyright (c) 2020 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.


from pysys.constants import *
from pysys.basetest import BaseTest
import urllib.request
import xml.etree.ElementTree as ET
import os
import inspect
import hashlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))))
from apamax.eplapplications.eplapps import EPLApps
from apamax.eplapplications.platform import CumulocityPlatform
from apamax.eplapplications.connection import C8yConnection

APPLICATION_NAME = 'pysys-test-application'
APPLICATION_KEY = 'pysys-test-key'

class ApamaC8YBaseTest(BaseTest):
	"""
	Base test for EPL Applications tests.

	Requires the following to be set on the project in pysysproject.xml file (typically from the environment):

	- EPL_TESTING_SDK
	- APAMA_HOME - only if running a local correlator
	"""

	def setup(self):
		super(ApamaC8YBaseTest, self).setup()
		self.modelId = 0 
		self.TEST_DEVICE_PREFIX = "PYSYS_" 
		# connect to the platform
		self.platform = CumulocityPlatform(self)

	def createAppKey(self, url, username, password):
		"""
			Checks if the tenant has an external application defined for us and if not, creates it.
			:param url: The URL to the Cumulocity tenant.
			:param username: The user to authenticate to the tenant.
			:param password: The password to authenticate to the tenant.

			:return: A app key suitable for connecting a test correlator to the tenant.
		"""
		try:
			conn = C8yConnection(url, username, password)
			res = conn.do_get(f'/application/applicationsByName/{APPLICATION_NAME}')
			if len(res['applications']) == 0:
				conn.do_request_json('POST', '/application/applications', body={"name":APPLICATION_NAME,"key":APPLICATION_KEY,"externalUrl":"http://www.softwareag.com","manifest":{},"type":"EXTERNAL"})
				return APPLICATION_KEY
			else:
				return res['applications'][0]['key']
		except Exception as e:
			self.abort(BLOCKED, f"Failure to create application key for remote access: {e}")

	def createProject(self, name, existingProject=None):
		"""
			Create a ProjectHelper object which mimics the Cumulocity EPL applications environment.

			Adds all the required bundles and adds the properties to connect and authenticate to the configured Cumulocity tenant.

			:param name: The name of the project
			:param existingProject: If provided the path to an existing project. The environment will be added to that project instead of a new one.
		"""
		# only import apama.project when calling this function which requires it
		try:
			from apama.project import ProjectHelper
		except:
			self.abort(BLOCKED, "Could not load Apama extensions. Try running from an Apama installation")
		# create the project and add required bundles
		apama_project = ProjectHelper(self, name)
		apama_project.create(existingProject) 

		# need to have a version independent addition or this will need to be maintained.
		apama_project.addBundle("Automatic onApplicationInitialized")
		apama_project.addBundle("Cumulocity IoT > Cumulocity Client 10.5+")
		apama_project.addBundle("Cumulocity IoT > Event Definitions for Cumulocity 10.5+")
		apama_project.addBundle("Cumulocity IoT > Utilities for Cumulocity 10.5+")
		apama_project.addBundle("Correlator Management")
		apama_project.addBundle("JSON Support")
		apama_project.addBundle("Time Format")
		apama_project.addBundle("The MemoryStore")
		return apama_project

	def addC8YPropertiesToProject(self, apamaProject, params=None):
		"""adds the connection parameters into the project
		
		:param params: dictionary to override and add to those defined for the project::
		
			<property name="CUMULOCITY_USERNAME" value="my-user"/>
			<property name="CUMULOCITY_PASSWORD" value="my-password"/>
			<property name="CUMULOCITY_SERVER_URL" value="https://my-url/"/>
			<property name="CUMULOCITY_AUTHORITY_FILE" value=""/>
			<property name="CUMULOCITY_TENANT" value=""/>
			<property name="CUMULOCITY_MEASUREMENT_FORMAT" value=""/>
		"""
		# we create a properties file at this point that will get copied into the project 
		paramImpl = {}
		paramImpl["CUMULOCITY_USERNAME"] = self.project.CUMULOCITY_USERNAME
		paramImpl["CUMULOCITY_PASSWORD"] = self.project.CUMULOCITY_PASSWORD
		paramImpl["CUMULOCITY_APPKEY"] = self.createAppKey(self.project.CUMULOCITY_SERVER_URL, self.project.CUMULOCITY_USERNAME, self.project.CUMULOCITY_PASSWORD)
		paramImpl["CUMULOCITY_SERVER_URL"] = self.project.CUMULOCITY_SERVER_URL
		paramImpl["CUMULOCITY_AUTHORITY_FILE"] = getattr(self.project, 'CUMULOCITY_AUTHORITY_FILE', '')
		paramImpl["CUMULOCITY_MEASUREMENT_FORMAT"] = getattr(self.project, 'CUMULOCITY_MEASUREMENT_FORMAT', 'BOTH')
		paramImpl['CUMULOCITY_TENANT'] = getattr(self.project, 'CUMULOCITY_TENANT', '')
		paramImpl['CUMULOCITY_FORCE_INITIAL_HOST'] = getattr(self.project, 'CUMULOCITY_FORCE_INITIAL_HOST', 'true')
		if params is not None:	
			for prop in params:
				paramImpl[prop] = params[prop]
		
		propFileName = os.path.join(self.output, "CumulocityIoT.properties")
		destFileName = "/connectivity/CumulocityClient10.5+/CumulocityIoT.properties"
		#create a local props file 
		with open(propFileName, "w", encoding='utf8') as propfile:
			propfile.write('\ufeff\n')
			for prop in paramImpl:
				propfile.write(prop + "=" + paramImpl[prop] + '\n')
		self.copy(propFileName, apamaProject.configDir() + destFileName)

	def getTestSubjectEPLApps(self):
		"""
			Retrieves a list of paths to EPL App(s) being tested.  
			If the user defines the <user-data name="EPLApp" value="EPLAppToBeTested"/> tag in the pysystest.xml file,
			then we just return the EPL App defined by the tag's value. 
			If this tag is not defined (or the value is an empty string) then all the mon files in project.EPL_APPS directory are returned.
		"""
		# Check EPL_APPS env is valid
		if not os.path.isdir(self.project.EPL_APPS):
			self.abort(BLOCKED, f'{self.project.EPL_APPS} is not a valid path.')

		eplAppsPaths = []
		# Check is user has defined the <user-data name="EPLApp" value="EPLAppToBeTested"/>
		if self.descriptor.userData.get('EPLApp'):
			eplApp = self.descriptor.userData['EPLApp']
			if not eplApp.endswith('.mon'):
				eplApp = eplApp + '.mon'
			# Check EPL App exists in project.EPL_APPS directory
			if not os.path.isfile(os.path.join(self.project.EPL_APPS, eplApp)):
				self.abort(BLOCKED, f'{eplApp} does not exist in {self.project.EPL_APPS}.')
			else:
				eplAppsPaths.append(os.path.join(self.project.EPL_APPS, eplApp))
		else:
			# If user has not defined EPLApp in pysystest.xml, return all files in project.EPL_APPS by default 
			eplAppsFiles = os.listdir(self.project.EPL_APPS)
			for eplApp in eplAppsFiles:
				# Check file is a .mon file before appending
				if os.path.splitext(eplApp)[1] == '.mon':
					eplAppsPaths.append(os.path.join(self.project.EPL_APPS, eplApp))
		return eplAppsPaths

	def prepareTenant(self):
		"""
			Prepares the tenant for a test by deleting all devices created by previous tests, and clearing all active alarms. 
		"""
		self.log.info('Preparing tenant to run test(s)')
		# Clear all active alarms
		self._clearActiveAlarms()
		# Delete devices that were created by tests
		self._deleteTestDevices()

	def _clearActiveAlarms(self):
		"""
			Clears all active alarms as part of a pre-test tenant cleanup. 
		"""
		self.log.info("Clearing active alarms")
		self.platform.getC8YConnection().do_request_json('PUT', '/alarm/alarms?status=ACTIVE', {"status": "CLEARED"})

	def _deleteTestDevices(self):
		"""
			Deletes all ManagedObjects that have name prefixed with "PYSYS_" and the 'c8y_isDevice' param as part of pre-test tenant cleanup.
		"""
		self.log.info("Deleting old test devices")
		# Retrieving test devices
		PAGE_SIZE = 100 	# By default, pageSize = 5 for querying to C8y
		resp = self.platform.getC8YConnection().do_get(
			"/inventory/managedObjects" +
			f"?query=has(c8y_IsDevice)+and+name+eq+'{self.TEST_DEVICE_PREFIX}*'" +
			f"&pageSize={PAGE_SIZE}&currentPage=1&withTotalPages=true")
		testDevices = resp['managedObjects']
		# Make sure we retrieve all pages from query
		TOTAL_PAGES = resp['statistics']['totalPages']
		if TOTAL_PAGES > 1:
			for currentPage in range(2, TOTAL_PAGES + 1):
				resp = self.platform.getC8YConnection().do_get(
					"/inventory/managedObjects" +
					f"?query=has(c8y_IsDevice)+and+name+eq+'{self.TEST_DEVICE_PREFIX}*'" +
					f"&pageSize={PAGE_SIZE}&currentPage={currentPage}")
				testDevices = testDevices + resp['managedObjects']
		
		# Deleting test devices
		testDeviceIds = [device['id'] for device in testDevices]
		for deviceId in testDeviceIds:
			resp = self.platform.getC8YConnection().request('DELETE', f'/inventory/managedObjects/{deviceId}')


class LocalCorrelatorSimpleTest(ApamaC8YBaseTest):
	""" 
		Base test for running test with no run.py with local correlator connected to Cumulocity IoT.
	"""

	def setup(self):
		super(LocalCorrelatorSimpleTest, self).setup()
		# Prepare the tenant for the test by performing a pre-test cleanup of artifacts from previous tests
		self.prepareTenant()

	def execute(self):
		"""
			Runs all the tests in the Input directory against the applications configured in the EPL_APPS 
			directory or with the EPLApps directive. 
		"""
		# Check APAMA_HOME and EPL_TESTING_SDK env are valid
		if not os.path.isdir(self.project.APAMA_HOME):
			self.abort(BLOCKED, f'APAMA_HOME project property is not valid ({self.project.APAMA_HOME}). Try running in an Apama command prompt.')
		if not os.path.isdir(self.project.EPL_TESTING_SDK):
			self.abort(BLOCKED, f'EPL_TESTING_SDK is not valid ({self.project.EPL_TESTING_SDK}). Please set the EPL_TESTING_SDK environment variable.')

		from apama.correlator import CorrelatorHelper
		# Create test project and add C8Y properties and EPL Apps 
		project = self.createProject("test-project")
		self.addC8YPropertiesToProject(project)
		eplApps = self.getTestSubjectEPLApps()
		self.addEPLAppsToProject(eplApps, project)
		project.deploy()
		self.waitForFile('CumulocityIoT.yaml',filedir=project.deployedDir()+'/config/connectivity/CumulocityClient10.5+/')

		# Run local correlator connected to C8Y with Apama EPL Apps and test files deployed
		correlator = CorrelatorHelper(self, name='c8y-correlator')              
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())

		# Wait for our EPL App test subjects to be added
		correlator.flush()

		# Inject test mon files from Input directory to correlator
		inputFiles = os.listdir(self.input)
		for inputFile in inputFiles:
			# Check file is a .mon file before injecting
			if os.path.splitext(inputFile)[1] == '.mon':
				self.log.info(f"Injecting {inputFile} test case")
				correlator.injectEPL(inputFile, self.input)
				# Wait for test to complete
				correlator.flush()
				activeTestMonitors = self.getMonitorsFromInjectedFile(correlator, os.path.join(self.input, inputFile))
				for monitor in activeTestMonitors:
					self.waitForGrep('c8y-correlator.log', expr=f"Removed monitor {monitor}", process=correlator)

	def validate(self):
		"""
			Checks than no errors were logged to the correlator log file.
		"""
		# look for log statements in the correlator log file
		self.log.info("Checking for errors")
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)

	def addEPLAppsToProject(self, eplApps, project):
		"""
			Adds the EPL app(s) being tested to a project. 
		"""
		for eplApp in eplApps:
			try:
				self.log.info(f'Adding {os.path.basename(eplApp)} to test project')
				self.copy(eplApp, project.monitorsDir() + os.path.basename(eplApp))
			except Exception as err:
				self.abort(BLOCKED, f'Error adding EPL app {eplApp} to test project: ' + str(err))

	def getMonitorsFromInjectedFile(self, correlator, file):
		"""
			Retrieves a list of active monitors in a correlator, added from a particular mon file 
			using GET request to http://correlator.host:correlator.port 
		"""
		monitors = []
		url = f'http://{correlator.host}:{correlator.port}'
		try:
			with open(file, 'rb') as f:
				filehash = hashlib.md5(f.read()).hexdigest()
				# GET request to http://correlator.host:correlator.port to retrieve active monitors
				req = urllib.request.Request(f'{url}/correlator/code/hash/list/{filehash}')
				with urllib.request.urlopen(req) as resp:
					xmlstring = str(resp.read(), 'utf-8')
					# Paring xml string to get the names of active monitors
					tree = ET.ElementTree(ET.fromstring(xmlstring))
					for mapItem in tree.getroot().iter('map'):
						isMon = False
						for prop in mapItem.iter('prop'):
							if prop.get('name') == 'type' and prop.text == "monitor":
								isMon = True
								continue # 'name' property follows after 'type' property
							if isMon and prop.get('name') == 'name':
								if prop.text not in monitors:
									monitors.append(prop.text)
								isMon = False
		except urllib.error.HTTPError as err:
			pass # it's OK if there aren't any monitors listed, or the hash can't be found, just means its already completed
		except Exception as err:
			self.abort(BLOCKED, 'Error retrieving injected monitors: ' + str(err))
		finally:
			return monitors

class EPLAppsSimpleTest(ApamaC8YBaseTest):
	"""
		Base test for running test with no run.py on EPL apps running in Cumulocity.
	"""

	def setup(self):
		super(EPLAppsSimpleTest, self).setup()
		# connect to the platform
		self.tests = None
		self.apps = None
		self.eplapps = None
		self.addCleanupFunction(lambda: self.shutdown())
		self.EPL_APP_PREFIX = self.TEST_DEVICE_PREFIX
		self.EPL_TEST_APP_PREFIX = self.EPL_APP_PREFIX + "TEST_"
		# Check EPL_TESTING_SDK env is set
		if not os.path.isdir(self.project.EPL_TESTING_SDK):
			self.abort(BLOCKED, f'EPL_TESTING_SDK is not valid ({self.project.EPL_TESTING_SDK}). Please set the EPL_TESTING_SDK environment variable.')
		self.eplapps = EPLApps(self.platform.getC8YConnection())
		self.prepareTenant()

	def prepareTenant(self):
		"""
			Prepares the tenant for a test by deleting all devices created by previous tests, deleting all EPL Apps which have been uploaded by tests, and clearing all active alarms. 
			
			This is done first so that there's no possibility existing test apps raising alarms or creating devices
		"""
		self._deleteTestEPLApps()
		super(EPLAppsSimpleTest, self).prepareTenant()


	def _deleteTestEPLApps(self):
		"""
			Deletes all EPL apps with name prefixed by "PYSYS_" or "PYSYS_TEST"
			as part of a pre-test tenant cleanup. 
		"""
		appsToDelete = []
		allApps = self.eplapps.getEPLApps(False)
		for eplApp in allApps:
			name = eplApp["name"]
			if name.startswith(self.EPL_APP_PREFIX):
				appsToDelete.append(name)
		if len(appsToDelete) > 0:
			self.log.info(f'Deleting the following EPL apps: {str(appsToDelete)}')
		for name in appsToDelete:
			self.eplapps.delete(name)

	def execute(self):
		"""
			Runs all the tests in the Input directory against the applications configured in the EPL_APPS 
			directory or with the EPLApps directive using EPL applications to run each test.
		"""
		# EPL Applications under test
		appPaths = self.getTestSubjectEPLApps()
		self.apps = [(self.EPL_APP_PREFIX + os.path.splitext(os.path.basename(appPaths[i]))[0], appPaths[i]) for i in range(len(appPaths))]
		
		if len(appPaths) > 0:
			self.log.info(f"Uploading {len(appPaths)} EPL application(s) from {os.path.normpath(self.project.EPL_APPS)}")

		for (name, path) in self.apps:
			# deploy the app and wait for it to start
			self.eplapps.deploy(path, name=name, redeploy=True, description='Application under test, injected by test framework')
			self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.'+name, errorExpr=['Error injecting monitorscript from file '+name])

		# Test application(s)
		testPaths = [os.path.join(self.input, x) for x in os.listdir(self.input) if x.endswith('.mon')]
		self.tests=[(self.EPL_TEST_APP_PREFIX + os.path.splitext(os.path.basename(testPaths[i]))[0], testPaths[i]) for i in range(0, len(testPaths))]
		
		if len(testPaths) > 0:
			self.log.info(f"Uploading {len(testPaths)} test case(s) from {self.input}")

		for (name, path) in self.tests:
			# deploy the test and wait for it to start
			self.eplapps.deploy(path, name=name, description='Test case, injected by test framework', redeploy=True)
			self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.'+name, errorExpr=['Error injecting monitorscript from file '+name])

			# wait until the test completes
			self.waitForGrep(self.platform.getApamaLogFile(), expr='Removed monitor eplfiles.'+name)
		
	def validate(self):
		"""
			Ensure that no errors were logged in the platform log file while we were running the test.
		"""
		self.log.info("Checking for errors")
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .*', contains=False)
		
	def shutdown(self):
		"""
			Deactivate all EPL apps which were uploaded when the test terminates.
		"""
		self.log.info("Deactivating EPL apps")
		# when we finish, deactivate anything we started
		if self.eplapps:
			for (name, _) in (self.apps or [])+(self.tests or []):
				try:
					self.eplapps.update(name, state='inactive')
				except Exception as e:
					self.log.info(f"Failed to deactivate app {name}: {e}")
