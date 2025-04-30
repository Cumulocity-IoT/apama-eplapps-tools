## License
# Copyright (c) 2020-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

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
import urllib, urllib.parse
import inspect
import hashlib
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))))
from apamax.eplapplications.eplapps import EPLApps
from apamax.eplapplications.platform import CumulocityPlatform
from apamax.eplapplications.connection import C8yConnection
from datetime import datetime, timezone

APPLICATION_NAME = 'pysys-test-application'
APPLICATION_KEY = 'pysys-test-key'

class ApamaC8YBaseTest(BaseTest):
	"""
	Base test for EPL applications tests.

	Requires the following to be set on the project in the pysysproject.xml file (typically from the environment):

	- EPL_TESTING_SDK
	- APAMA_HOME - Only if running a local correlator.
	"""

	def setup(self):
		super(ApamaC8YBaseTest, self).setup()
		# Check if the script is running on Windows
		# If it is, print a warning message and exit
		if os.name == 'nt':
			self.abort(BLOCKED, "Warning: The eplapp-tools is no longer supported natively on Windows environment. We recommend using a WSL-based setup with a Debian distribution.")

		# Check EPL_TESTING_SDK env is set
		if not os.path.isdir(self.project.EPL_TESTING_SDK):
			self.abort(BLOCKED, f'EPL_TESTING_SDK is not valid ({self.project.EPL_TESTING_SDK}). Please set the EPL_TESTING_SDK environment variable.')

		self.modelId = 0 
		self.TEST_DEVICE_PREFIX = "PYSYS_"
		self.EPL_APP_PREFIX = self.TEST_DEVICE_PREFIX
		# connect to the platform
		self.platform = CumulocityPlatform(self)

	def createAppKey(self, url, username, password):
		"""
			Checks if the tenant has an external application defined for us and if not, creates it.

			:param url: The URL to the Cumulocity IoT tenant.
			:param username: The user to authenticate to the tenant.
			:param password: The password to authenticate to the tenant.

			:return: An app key suitable for connecting a test correlator to the tenant.
		"""
		try:
			conn = C8yConnection(url, username, password)
			res = conn.do_get(f'/application/applicationsByName/{APPLICATION_NAME}')
			if len(res['applications']) == 0:
				conn.do_request_json('POST', '/application/applications', body={"name":APPLICATION_NAME,"key":APPLICATION_KEY,"externalUrl":"http://www.softwareag.com","manifest":{},"type":"EXTERNAL","noAppSwitcher":True})
				return APPLICATION_KEY
			else:
				return res['applications'][0]['key']
		except Exception as e:
			self.abort(BLOCKED, f"Failure to create application key for remote access: {e}")

	def createProject(self, name, existingProject=None):
		"""
			Creates a `ProjectHelper` object which mimics the Cumulocity IoT EPL applications environment.

			Adds all the required bundles and adds the properties to connect and authenticate to the configured Cumulocity IoT tenant.

			:param name: The name of the project.
			:param existingProject: If provided the path to an existing project. The environment will be added to that project instead of a new one.
			:return: A `ProjectHelper` object.
		"""
		# only import apama.project when calling this function which requires it
		try:
			from apama.project import ProjectHelper
		except:
			self.abort(BLOCKED, "Could not load Apama extensions. Try running from an Apama installation")
		# create the project and add required bundles
		apama_project = ProjectHelper(self, name)
		apama_project.create(existingProject) 

		n2 = getattr(self.project, 'CUMULOCITY_NOTIFICATIONS_2', 'false')

		# need to have a version independent addition or this will need to be maintained.
		apama_project.addBundle("Automatic onApplicationInitialized")
		if n2 == 'false':
			apama_project.addBundle("Cumulocity IoT > Cumulocity Client")
		else:
			apama_project.addBundle("Cumulocity IoT > Cumulocity Notifications 2.0")
		apama_project.addBundle("Cumulocity IoT > Event Definitions for Cumulocity")
		apama_project.addBundle("Cumulocity IoT > Utilities for Cumulocity")
		apama_project.addBundle("Correlator Management")
		apama_project.addBundle("JSON Support")
		apama_project.addBundle("Time Format")
		apama_project.addBundle("Functional EPL Library")
		apama_project.addBundle("The MemoryStore")
		return apama_project

	def addC8YPropertiesToProject(self, apamaProject, params=None):
		"""Adds the connection parameters into a project.
		
		:param apamaProject: The `ProjectHelper` object for a project.
		:param params: The dictionary of parameters to override and add to those defined for the project::
		
			<property name="CUMULOCITY_USERNAME" value="my-user"/>
			<property name="CUMULOCITY_PASSWORD" value="my-password"/>
			<property name="CUMULOCITY_SERVER_URL" value="https://my-url/"/>
			<property name="CUMULOCITY_AUTHORITY_FILE" value=""/>
			<property name="CUMULOCITY_TENANT" value=""/>
			<property name="CUMULOCITY_MEASUREMENT_FORMAT" value=""/>
		"""
		def create_properties_file(output_name, dest_file, properties):
			"""Creates a local properties file and copies it to the destination."""
			with open(os.path.join(self.output, output_name), "w", encoding='utf8') as propfile:
				propfile.write('\ufeff\n')
				for prop, value in properties.items():
					propfile.write(f"{prop}={value}\n")
			self.copy(output_name, apamaProject.configDir() + dest_file)

		if params is None:
			params = {}

		n2 = getattr(self.project, 'CUMULOCITY_NOTIFICATIONS_2', 'false')

		# we create a properties file at this point that will get copied into the project 
		paramImpl = {
			"CUMULOCITY_USERNAME": self.project.CUMULOCITY_USERNAME,
			"CUMULOCITY_PASSWORD": self.project.CUMULOCITY_PASSWORD,
			"CUMULOCITY_APPKEY": self.createAppKey(self.project.CUMULOCITY_SERVER_URL, self.project.CUMULOCITY_USERNAME, self.project.CUMULOCITY_PASSWORD),
			"CUMULOCITY_SERVER_URL": self.project.CUMULOCITY_SERVER_URL,
			"CUMULOCITY_AUTHORITY_FILE": getattr(self.project, 'CUMULOCITY_AUTHORITY_FILE', ''),
			"CUMULOCITY_MEASUREMENT_FORMAT": getattr(self.project, 'CUMULOCITY_MEASUREMENT_FORMAT', 'BOTH'),
			"CUMULOCITY_TENANT": getattr(self.project, 'CUMULOCITY_TENANT', ''),
			"CUMULOCITY_FORCE_INITIAL_HOST": getattr(self.project, 'CUMULOCITY_FORCE_INITIAL_HOST', 'true'),
			"CUMULOCITY_PROXY_HOST": '',
			"CUMULOCITY_PROXY_PORT": '',
			"CUMULOCITY_PROXY_USERNAME": '',
			"CUMULOCITY_PROXY_PASSWORD": ''
		}

		paramImpl.update(params)

		if n2 == 'false':
			create_properties_file("CumulocityIoT.properties", "/connectivity/CumulocityClient/CumulocityIoT.properties", paramImpl)
		else:	
			create_properties_file("CumulocityIoT.properties", "/connectivity/CumulocityNotifications2.0/CumulocityIoTREST.properties", paramImpl)

			n2props = {
				"CUMULOCITY_NOTIFICATIONS_SUBSCRIBER_NAME": "streamingAnalytics",
				"CUMULOCITY_NOTIFICATIONS_SUBSCRIPTION_NAME": "streamingAnalytics",
				"CUMULOCITY_NOTIFICATIONS_SUBSCRIPTION_TYPE": "KeyShared",
				"CUMULOCITY_NOTIFICATIONS_NUMBER_CLIENTS": "1",
				"CUMULOCITY_NOTIFICATIONS_MAX_BUFFERSIZE": "1000",
				"CUMULOCITY_NOTIFICATIONS_MAX_BATCHSIZE": "1000",
				"CUMULOCITY_NOTIFICATIONS_AUTO_START": "True",
				"CUMULOCITY_NOTIFICATIONS_SERVICE_URL": getattr(self.project, 'CUMULOCITY_NOTIFICATIONS_SERVICE_URL', 'pulsar://pulsar-proxy')
			}

			n2props.update(params)
			create_properties_file("CumulocityNotifications2.properties", "/connectivity/CumulocityNotifications2.0/CumulocityNotifications2.properties", n2props)

	def getTestSubjectEPLApps(self):
		"""
			Retrieves a list of paths to the EPL apps being tested.

			If the user defines the `<user-data name="EPLApp" value="EPLAppToBeTested"/>` tag in the pysystest.xml file, 
			then we just return the EPL app defined by the tag's value. If this tag is not defined (or the value is an empty string) 
			then all the mon files in the project.EPL_APPS directory are returned.
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
			# If user has not defined EPLApp in pysystest.xml, return all files in project.EPL_APPS by default 
			eplAppsFiles = os.listdir(self.project.EPL_APPS)
			for eplApp in eplAppsFiles:
				# Check file is a .mon file before appending
				if os.path.splitext(eplApp)[1] == '.mon':
					eplAppsPaths.append(os.path.join(self.project.EPL_APPS, eplApp))
		return eplAppsPaths

	def prepareTenant(self, tenant=None):
		"""
		Prepares the tenant for a test by deleting all devices created by previous tests and clearing all active alarms.
		However, you can disable the default behavior of clearing all active alarms by setting the `clearAllActiveAlarmsDuringTenantPreparation` property to `false` in the PySys project configuration.

		:param tenant: The Cumulocity IoT tenant. If no tenant is specified, the tenant configured in the pysysproject.xml file is prepared.
		:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		"""
		self.log.info('Preparing tenant to run test(s)')
		# Clear all active alarms
		self._clearActiveAlarms(tenant=tenant)
		# Delete devices that were created by tests
		self._deleteTestDevices(tenant=tenant)

	def createTestDevice(self, name, type='PySysTestDevice', children=None, tenant=None):
		"""
		Creates a Cumulocity IoT device for testing.

		:param str name: The name of the device. The name of the device is prefixed with `PYSYS_` so that the framework can identify and clean up test devices.
		:param type: The type of the device.
		:type type: str, optional
		:param children: The list of device IDs to add them as children to the created device.
		:type children: list[str], optional
		:param tenant: The Cumulocity IoT tenant. If no tenant is specified, the tenant configured in the pysysproject.xml file is used.
		:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		:return: The ID of the device created.
		:rtype: str
		"""
		connection = (tenant or self.platform.getTenant()).getConnection()
		device = {
			'name': f'{self.TEST_DEVICE_PREFIX}{name}',
			'c8y_IsDevice': True,
			'type': type,
			'com_cumulocity_model_Agent': {}
		}
		id = json.loads(connection.do_request_json('POST', '/inventory/managedObjects', device, useLocationHeaderPostResp=False))['id']
		
		children = children or []
		for child in children:
			connection.do_request_json('POST', f'/inventory/managedObjects/{id}/childDevices', {'managedObject': {'id': child}})
		return id

	def getAlarms(self, source=None, type=None, status=None, dateFrom=None, dateTo=None, tenant=None, **kwargs):
		"""
		Gets all alarms with matching parameters.

		For example::
		
			self.getAlarms(type='my_alarms', dateFrom='2021-04-15 11:00:00.000Z', 
							dateTo='2021-04-15 11:30:00.000Z')

		:param source: The source object of the alarm. Get alarms for all objects if not specified.
		:type source: str, optional
		:param type: The type of alarm to get. Get alarms of all types if not specified.
		:type type: str, optional
		:param status: The status of the alarms to get. Get alarms of all status if not specified.
		:type status: str, optional
		:param dateFrom: The start time of the alarm in the ISO format. If specified, only alarms that are created on or after this time are fetched.
		:type dateFrom: str, optional
		:param dateTo: The end time of the alarm in the ISO format. If specified, only alarms that are created on or before this time are fetched.
		:type dateTo: str, optional
		:param tenant: The Cumulocity IoT tenant. If no tenant is specified, the tenant configured in the pysysproject.xml file is used.
		:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		:param \\**kwargs: All additional keyword arguments are treated as extra parameters for filtering alarms. 
		:return: List of alarms.
		:rtype: list[object]
		"""
		queryParams = {}
		if source:
			queryParams['source'] = source
		if type:
			queryParams['type'] = type
		if status:
			queryParams['status'] = status
		if dateFrom:
			queryParams['dateFrom'] = dateFrom
		if dateTo:
			queryParams['dateTo'] = dateTo		
		if kwargs:
			queryParams.update(kwargs)
			
		return self._getCumulocityObjectCollection('/alarm/alarms', queryParams=queryParams, responseKey='alarms',tenant=tenant)

	def getOperations(self, deviceId=None, fragmentType=None, dateFrom=None, dateTo=None, tenant=None, **kwargs):
		"""
		Gets all operations with matching parameters.

		For example::
		
			self.getOperations(fragmentType='my_ops', dateFrom='2021-04-15 11:00:00.000Z', 
								dateTo='2021-04-15 11:30:00.000Z')

		:param deviceId: The device ID of the alarm. Get operations for all devices if not specified.
		:type deviceId: str, optional
		:param fragmentType: The type of fragment that must be part of the operation.
		:type fragmentType: str, optional
		:param dateFrom: The start time of the operation in the ISO format. If specified, only operations that are created on or after this time are fetched.
		:type dateFrom: str, optional
		:param dateTo: The end time of the operation in the ISO format. If specified, only operations that are created on or before this time are fetched.
		:type dateTo: str, optional
		:param tenant: The Cumulocity IoT tenant. If no tenant is specified, the tenant configured in the pysysproject.xml file is used.
		:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		:param \\**kwargs: All additional keyword arguments are treated as extra parameters for filtering operations.
		:return: List of operations.
		:rtype: list[object]
		"""

		queryParams = {}
		if deviceId:
			queryParams['deviceId'] = deviceId
		if fragmentType:
			queryParams['fragmentType'] = fragmentType
		if dateFrom:
			queryParams['dateFrom'] = dateFrom
		if dateTo:
			queryParams['dateTo'] = dateTo
		if kwargs:
			queryParams.update(kwargs)
		
		return self._getCumulocityObjectCollection('/devicecontrol/operations', queryParams=queryParams, responseKey='operations',tenant=tenant)

	def copyWithReplace(self, sourceFile, targetFile, replacementDict, marker='@'):
		"""
			Copies the source file to the target file and replaces the placeholder strings with the actual values.

			:param sourceFile: The path to the source file to copy.
			:type sourceFile: str
			:param targetFile: The path to the target file.
			:type targetFile: str
			:param replacementDict: A dictionary containing placeholder strings and their actual values to replace.
			:type replacementDict: dict[str, str]
			:param marker: Marker string used to surround replacement strings in the source file to disambiguate from normal strings. For example, `@`.
			:type marker: str, optional	
		"""
		def mapper(line):
			for key, value in replacementDict.items():
				line = line.replace(f'{marker}{key}{marker}', str(value))
			return line
		self.copy(sourceFile, targetFile, mappers=[mapper])
		
	def _getCumulocityObjectCollection(self, resourceUrl, queryParams, responseKey, tenant=None):
		"""
			Gets all Cumulocity IoT object collection.

			Fetches all pages of the collection.

			:param str resourceUrl: The base url of the object to get. For example, /alarm/alarms.
			:param dict[str,str] queryParams: The query parameters.
			:param str responseKey: The key to use to get actual object list from the response JSON.
			:param tenant: The Cumulocity IoT tenant.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
			:return: List of all object.
			:rtype: list[dict]
		"""
		result = []
		PAGE_SIZE = 100 	# By default, pageSize = 5 for querying to C8y
		queryParams = queryParams or {}

		connection = (tenant or self.platform.getTenant()).getConnection()
		
		def create_url(**params):
			p = queryParams.copy()
			p.update(params)
			if '?' in resourceUrl:
				return f'{resourceUrl}&{urllib.parse.urlencode(p)}'
			else:
				return f'{resourceUrl}?{urllib.parse.urlencode(p)}'

		resp = connection.do_get(create_url(pageSize=PAGE_SIZE, currentPage=1, withTotalPages=True))

		result += resp[responseKey]
		# Make sure we retrieve all pages from query
		TOTAL_PAGES = resp['statistics']['totalPages']
		if TOTAL_PAGES > 1:
			for currentPage in range(2, TOTAL_PAGES + 1):
				resp = connection.do_get(create_url(pageSize=PAGE_SIZE, currentPage=currentPage))
				result += resp[responseKey]

		return result

	def _clearActiveAlarms(self,tenant=None):
		"""
			Clears all active alarms as part of a pre-test tenant cleanup.

			:param tenant: The Cumulocity IoT tenant.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		"""
		# EPL Apps tools doesn't cleanup all alarms on tenant by default
		if getattr(self.project, 'clearAllActiveAlarmsDuringTenantPreparation', 'true').lower() == 'false': 
			self.log.info(f'Skipping the alarm cleanup operation due to property clearAllActiveAlarmsDuringTenantPreparation is false')
			return

		self.log.info("Clearing active alarms")
		connection = (tenant or self.platform.getTenant()).getConnection()
		connection.do_request_json('PUT', '/alarm/alarms?status=ACTIVE', {"status": "CLEARED"})

	def _deleteTestDevices(self,tenant=None):
		"""
			Deletes all ManagedObjects that have name prefixed with "PYSYS_" and the 'c8y_isDevice' param as part of pre-test tenant cleanup.

			:param tenant: The Cumulocity IoT tenant.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional

		"""
		connection = (tenant or self.platform.getTenant()).getConnection()
		self.log.info("Deleting old test devices")
		testDevices = self._getCumulocityObjectCollection(f"/inventory/managedObjects", 
						queryParams={'query':f"has(c8y_IsDevice) and name eq '{self.TEST_DEVICE_PREFIX}*'"},
						responseKey='managedObjects',tenant=tenant)
		# Deleting test devices
		testDeviceIds = [device['id'] for device in testDevices]
		for deviceId in testDeviceIds:
			resp = connection.request('DELETE', f'/inventory/managedObjects/{deviceId}')

	def _deleteTestEPLApps(self,tenant=None):
		"""
			Deletes all EPL apps with name prefixed by "PYSYS_" or "PYSYS_TEST"
			as part of a pre-test tenant cleanup. 

			:param tenant: The Cumulocity IoT tenant.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		"""

		if not self.platform.supportsEPLApps(): return
		connection = (tenant or self.platform.getTenant()).getConnection()
		eplapps = EPLApps(connection)
		appsToDelete = []
		allApps = eplapps.getEPLApps(False)
		for eplApp in allApps:
			name = eplApp["name"]
			if name.startswith(self.EPL_APP_PREFIX):
				appsToDelete.append(name)
		if len(appsToDelete) > 0:
			self.log.info(f'Deleting the following EPL apps: {str(appsToDelete)}')
		for name in appsToDelete:
			eplapps.delete(name)

	def getUTCTime(self, timestamp=None):
		""" 
			Gets a Cumulocity IoT-compliant UTC timestamp string for the current time or the specified time.

			:param timestamp: The epoc timestamp to get timestamp string for. Use current time if not specified.
			:type timestamp: float, optional
			:return: Timestamp string.
			:rtype: str
		"""
		if timestamp is not None:
			t = datetime.fromtimestamp(timestamp, timezone.utc)
		else:
			t = datetime.now(timezone.utc)
		return t.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

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
			directory or with the `EPLApps` directive. 
		"""
		# Check APAMA_HOME env is set
		if not os.path.isdir(self.project.APAMA_HOME):
			self.abort(BLOCKED, f'APAMA_HOME project property is not valid ({self.project.APAMA_HOME}). Try running in an Apama command prompt.')

		from apama.correlator import CorrelatorHelper
		# Create test project and add C8Y properties and EPL Apps 
		project = self.createProject("test-project")
		self.addC8YPropertiesToProject(project)
		eplApps = self.getTestSubjectEPLApps()
		self.addEPLAppsToProject(eplApps, project)
		project.deploy()

		# Run local correlator connected to C8Y with Apama EPL Apps and test files deployed
		correlator = CorrelatorHelper(self, name='c8y-correlator')              
		correlator.start(logfile='c8y-correlator.log', config=project.deployedDir())

		# Wait for our EPL App test subjects to be added
		correlator.flush()

		self.waitForGrep('c8y-correlator.log', expr="Connected to Cumulocity IoT")

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
			Checks that no errors were logged to the correlator log file.
		"""
		# look for log statements in the correlator log file
		self.log.info("Checking for errors")
		self.assertGrep('c8y-correlator.log', expr=' (ERROR|FATAL) .*', contains=False)

	def addEPLAppsToProject(self, eplApps, project):
		"""
			Adds the EPL app(s) being tested to a project. 
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
			using a GET request to http://correlator.host:correlator.port.
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
		Base test for running test with no run.py on EPL apps running in Cumulocity IoT.
	"""

	def setup(self):
		super(EPLAppsSimpleTest, self).setup()
		# connect to the platform
		self.tests = None
		self.apps = None
		self.eplapps = None
		self.addCleanupFunction(lambda: self.shutdown())
		self.EPL_TEST_APP_PREFIX = self.EPL_APP_PREFIX + "TEST_"

		self.eplapps = EPLApps(self.platform.getC8YConnection())
		self.prepareTenant()

	def prepareTenant(self,tenant=None):
		"""
			Prepares the tenant for a test by deleting all devices created by previous tests, deleting all EPL apps which have been uploaded by tests, and clearing all active alarms. 
			
			This is done first so that it is not possible for existing test apps to raise alarms or create devices.
		"""
		self._deleteTestEPLApps(tenant)
		super(EPLAppsSimpleTest, self).prepareTenant(tenant)

	def execute(self):
		"""
			Runs all the tests in the Input directory against the applications configured in the EPL_APPS 
			directory or with the `EPLApps` directive using EPL apps to run each test.
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
			Ensures that no tests failed.
		"""
		self.log.info("Checking for errors")
		self.assertGrep(self.platform.getApamaLogFile(), expr=' (ERROR|FATAL) .* eplfiles\.', contains=False)
		
	def shutdown(self):
		"""
			Deactivates all uploaded EPL apps when the test terminates.
		"""
		self.log.info("Deactivating EPL apps")
		# when we finish, deactivate anything we started
		if self.eplapps:
			for (name, _) in (self.apps or [])+(self.tests or []):
				try:
					self.eplapps.update(name, state='inactive')
				except Exception as e:
					self.log.info(f"Failed to deactivate app {name}: {e}")
