## License
# Copyright (c) 2020-2022 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
from pysys.constants import *
import json
import urllib, urllib.error
import sys, os, time, pathlib, glob
import csv
import math, statistics
from pysys.utils.linecount import linecount
from apamax.eplapplications.basetest import ApamaC8YBaseTest
from apamax.eplapplications.eplapps import EPLApps
from apamax.eplapplications.smartrules import SmartRulesManager

# constants for performance metrics strings.
PERF_TIMESTAMP = 'timestamp'
PERF_TOTAL_MEMORY_USAGE = 'total_memory_usage'
PERF_MEMORY_CORR = 'memory_usage_corr'
PERF_MEMORY_APCTRL = 'memory_usage_apctrl'
PERF_CORR_IQ_SIZE = 'correlator_iq_size'
PERF_CORR_OQ_SIZE = 'correlator_oq_size'
PERF_CORR_SPAW_RATE = 'correlator_swap_read_write'
PERF_CORR_NUM_OUTPUT_SENT = 'correlator_num_output_sent'
PERF_CORR_NUM_INPUT_RECEIVED = 'correlator_num_input_received'
PERF_CEP_PROXY_REQ_STARTED = 'cep_proxy_requests_started'
PERF_CEP_PROXY_REQ_COMPLETED = 'cep_proxy_requests_completed'
PERF_CEP_PROXY_REQ_FAILED = 'cep_proxy_requests_failed'
PERF_CPU_USAGE_MILLI = 'cpu_usage_milli'

# Description of metrics. Order is important as it determines the order of fields in the final HTML report table
METRICS_DESCRIPTION = {
	PERF_TOTAL_MEMORY_USAGE: 'Total Memory Usage (MB)',
	PERF_MEMORY_CORR: 'Correlator Memory Usage (MB)',
	PERF_MEMORY_APCTRL: 'Apama-ctrl Memory Usage (MB)',
	PERF_CORR_IQ_SIZE: 'Correlator Input Queue Size',
	PERF_CORR_OQ_SIZE: 'Correlator Output Queue Size',
	PERF_CORR_SPAW_RATE: 'Correlator Swapping Rate',
	PERF_CPU_USAGE_MILLI: 'CPU Usage (millicpu)',
	PERF_CORR_NUM_INPUT_RECEIVED: 'Number of Inputs Received',
	PERF_CORR_NUM_OUTPUT_SENT: 'Number of Outputs Sent',
	PERF_CEP_PROXY_REQ_STARTED: 'CEP Requests Started',
	PERF_CEP_PROXY_REQ_COMPLETED: 'CEP Requests Completed',
	PERF_CEP_PROXY_REQ_FAILED: 'CEP Requests Failed',
}

# constants for output files
OUTFILE_PERF_RAW_DATA = 'perf_raw_data'
OUTFILE_PERF_CPU_USAGE = 'perf_cpuusage'
OUTFILE_PERF_STATS = 'perf_statistics'
OUTFILE_PERF_COUNTERS = 'perf_counters'
OUTFILE_ENV_DETAILS = 'env_details'

class ObjectCreator:
	"""
		Base class for object creator implementation.
	"""
	def createObject(self, device, time):
		"""
			Creates an object to publish.

			:param str device: The ID of the device to create an object for.
			:param str time: The source time to use for the object.
			:return: A new object instance to publish.
			
			For example::
			
			    # Create and return a measurement object
			    return {
			        'time': time,
			        "type": 'my_measurement',
			        "source": { "id": device },
			        'my_fragment': {
			            'my_series': {
			                "value": random.uniform(0, 100)
			            }
			        }
			    }
		"""
		raise Exception('Not Implemeted')

class ApamaC8YPerfBaseTest(ApamaC8YBaseTest):
	"""
	Base class for performance tests for EPL apps and smart rules.

	Requires the following to be set on the project in the pysysproject.xml file (typically from the environment):

	- EPL_TESTING_SDK

	:ivar eplapps: The object for deploying and undeploying EPL apps.
	:vartype eplapps: :class:`~apamax.eplapplications.eplapps.EPLApps`
	:ivar smartRulesManager: The object for managing smart rules.
	:vartype smartRulesManager: :class:`~apamax.eplapplications.smartrules.SmartRulesManager`
	"""

	def setup(self):
		super(ApamaC8YPerfBaseTest, self).setup()
		self.addCleanupFunction(lambda: self._shutdown())
		self.eplapps = EPLApps(self.platform.getC8YConnection())
		self.smartRulesManager = SmartRulesManager(self.platform.getTenant(), self.log)

		self.perfMonitorThread = None 	# Current performance monitoring thread
		self.perfMonitorCount = 0		# Number of time performance monitoring is started
		self.simulators = {}			# All simulators per tenant

	def prepareTenant(self, restartMicroservice=False,tenant=None):
		"""
			Prepares the tenant for a performance test by deleting all devices created by previous tests, deleting all EPL test applications, and clearing all active alarms.

			This must be called by the test before the application is deployed.

			:param bool restartMicroservice: Restart the Apama-ctrl microservice.
			:param tenant: The Cumulocity IoT tenant. If no tenant is specified, the tenant configured in the pysysproject.xml file is prepared.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		"""
		tenantId = (tenant or self.platform.getTenant()).getTenantId()
		self.log.info(f'Preparing tenant {tenantId} to run performance test')

		# Stop any running simulators
		self._stopSimulators(tenantId)

		# Delete existing EPL test apps
		self._deleteTestEPLApps(tenant)
		
		# Clear all active alarms
		self._clearActiveAlarms(tenant)
		
		# Delete devices that were created by tests
		self._deleteTestDevices(tenant)
		
		# Delete all smartrules created by the tests
		self._deleteTestSmartRules(tenant)

		# Stop monitoring thread
		if self.perfMonitorThread:
			# Do not stop perf monitoring thread if testing against multi-tenant microservice
			# and tenant is specified explicitly. because we need to monitor all tenants at once.
			if not (self.platform.isMultiTenantMicroservice() and tenant is not None):
				self.perfMonitorThread.stop()
				self.perfMonitorThread.join()

		if restartMicroservice:
			self._restartApamaMicroserviceImpl()

	def _shutdown(self):
		"""
		Performs common cleanup during test shutdown, like stopping performance monitoring thread, deactivating EPL test apps, and generating final HTML report.
		"""
		if self.perfMonitorThread:
			self.perfMonitorThread.stop()
			self.perfMonitorThread.join()
		self._disableTestSmartRules()
		self._deactivateTestEPLApps()
		self._generateFinalHTMLReport()
		for t in self.simulators.keys():
			self._stopSimulators(t)

	def _stopSimulators(self, tenantId):
		""" Stop running simulators for the specified tenant ID. """
		if tenantId in self.simulators:
			simulators = self.simulators[tenantId]
			for s in simulators:
				try:
					s.stop()
				except Exception as ex:
					self.log.warn(f'Failed to stop simulator: {ex}')
			self.simulators[tenantId] = []

	def _deleteTestEPLApps(self,tenant=None):
		super()._deleteTestEPLApps(tenant)

	def _disableTestSmartRules(self):
		""" As part of test cleanup, disable smart rules created by the framework for all tenants."""
		for tenant in self.platform.getSubscribedTenants():
			sm = SmartRulesManager(tenant, self.log)
			rules = sm.getAllSmartRules(withLocalRules=True)
			for rule in rules:
				if rule._isTestSmartRule():
					rule.setEnabled(False)
					rule.deploy()

	def _deleteTestSmartRules(self,tenant=None):
		"""
		Delete smart rules created by the framework.
		
		:param tenant: The Cumulocity IoT tenant. If no tenant is specified, smart rules are deleted from the tenant configured in the pysysproject.xml file.
		:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`, optional
		"""
		self.log.info("Clearing test smart rules")
		sm = self.smartRulesManager
		if tenant is not None:
			sm = SmartRulesManager(tenant, self.log)
		
		existingSmartRules = sm.getAllSmartRules(withLocalRules=True)
		for rule in existingSmartRules:
			if rule._isTestSmartRule():
				rule.delete()

	def restartApamaMicroservice(self):
		"""
			Restarts the Apama-ctrl microservice and waits for it to come back up.
		"""
		self._restartApamaMicroserviceImpl()

	def _restartApamaMicroserviceImpl(self):
		""" Restarts Apama-ctrl microservice and wait for it to come back up. """
		if self.platform.isSmartrulesOnlyMicroservice():
			# We cannot restart smartrules microservice
			self.log.info(f'Cannot restart {self.platform.getMicroserviceName()} microservice as it is not supported.')
			return
		self.log.info('Restarting Apama-ctrl microservice')
		count1 = linecount(self.platform.getApamaLogFile(), 'Microservice restart Microservice .* is being restarted')
		count2 = linecount(self.platform.getApamaLogFile(), 'httpServer-.*Started receiving messages')
		try:
			self.platform.getC8YConnection().do_request_json('PUT', '/service/cep/restart', {})
			self.log.info('Restart requested')
		except (urllib.error.HTTPError, urllib.error.URLError) as ex:
			statuscode = int(ex.code)
			if statuscode // 10 == 50:
				self.log.info('Restart requested')
			else:
				raise Exception(f'Failed to restart Apama-ctrl: {ex}')
		except Exception as ex:
			raise Exception(f'Failed to restart Apama-ctrl: {ex}')
		self.waitForGrep('platform.log', expr='Microservice restart Microservice .* is being restarted', condition=f'>={count1+1}')
		self.waitForGrep('platform.log', expr='httpServer-.*Started receiving messages', condition=f'>={count2+1}', timeout=TIMEOUTS['WaitForProcess'])
		self.log.info('Apama-ctrl microservice is successfully restarted')

	def _deactivateTestEPLApps(self):
		"""
		Deactivates all EPL test apps as part of test cleanup.
		"""
		if self.platform.supportsEPLApps():
			eplapps = self.eplapps.getEPLApps(False) or []
			for app in eplapps:
				name = app["name"]
				if name.startswith(self.EPL_APP_PREFIX):
					try:
						self.eplapps.update(name, state='inactive')
					except Exception as e:
						self.log.info(f"Failed to deactivate app {name}: {e}")


	def startMeasurementSimulator(self, devices, perDeviceRate, creatorFile, creatorClassName, creatorParams, duration=None, processingMode='CEP', tenant=None):
		"""
			Starts a measurement simulator process to publish simulated measurements to Cumulocity IoT.

			The simulator uses an instance of the provided measurement creator class to create new measurements to send, 
			allowing the test to publish measurements of different types and sizes.
			The simulator looks up the specified class in the specified Python file and creates a new instance of the class
			using the provided parameters. The measurement creator class must extend the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.

			:param list[str] devices: List of device IDs to generate measurements for.
			:param float perDeviceRate: The rate of measurements to publish per device.
			:param str creatorFile: The path to the Python file containing the measurement creator class.
			:param str creatorClassName: The name of the measurement creator class that extends the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.
			:param list creatorParams: The list of parameters to pass to the constructor of the measurement creator class to create a new instance.
			:param str processingMode: Cumulocity IoT processing mode. Possible values are CEP, PERSISTENT, TRANSIENT, and QUIESCENT.
			:param duration: The duration (in seconds) to run the simulator for. If no duration is specified, then the simulator runs until either stopped or the end of the test.
			:type duration: float, optional
			:param tenant: The Cumulocity IoT tenant. If no tenant is specified, measurements are published to the tenant configured in the pysysproject.xml file.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`
			:return: The process handle of the simulator process.
			:rtype: L{pysys.process.Process}

			For example::

				# In a 'creator.py' file in test input directory.
				class MyMeasurementCreator(ObjectCreator):
				    def __init__(lowerBound, upperBound):
				        self.lowerBound = lowerBound
				        self.upperBound = upperBound
				    def createObject(self, device, time):
				        return {
				            'time': time,
				            "type": 'my_measurement',
				            "source": { "id": device },
				            'my_fragment': {
				                'my_series': {
				                    "value": random.uniform(self.lowerBound, self.upperBound)
				                }
				            }
		 		        }
				
				...

				# In the test
				self.startMeasurementSimulator(
				        ['12345'],                  # device IDs
				        1,                          # rate of measurements to publish
				        f'{self.input}/creator.py', # Python file path
				        'MyMeasurementCreator',     # class name
				        [10, 50],                   # constructor parameters for MyMeasurementCreator class
				    )
		"""
		return self._startPublisher(devices, perDeviceRate, '/measurement/measurements', creatorFile, creatorClassName, creatorParams, duration, processingMode,tenant=tenant)

	def startEventSimulator(self, devices, perDeviceRate, creatorFile, creatorClassName, creatorParams, duration=None, processingMode='CEP', tenant=None):
		"""
			Starts an event simulator process to publish simulated events to Cumulocity IoT.

			The simulator uses an instance of the provided event creator class to create new events to send, 
			allowing the test to publish events of different types and sizes.
			The simulator looks up the specified class in the specified Python file and creates a new instance of the class
			using the provided parameters. The event creator class must extend the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.

			:param list[str] devices: List of device IDs to generate events for.
			:param float perDeviceRate: The rate of events to publish per device.
			:param str creatorFile: The path to the Python file containing the event creator class.
			:param str creatorClassName: The name of the event creator class that extends the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.
			:param list creatorParams: The list of parameters to pass to the constructor of the event creator class to create a new instance.
			:param str processingMode: Cumulocity IoT processing mode. Possible values are CEP, PERSISTENT, TRANSIENT, and QUIESCENT.
			:param duration: The duration (in seconds) to run the simulator for. If no duration is specified, then the simulator runs until either stopped or the end of the test.
			:type duration: float, optional
			:param tenant: The Cumulocity IoT tenant. If no tenant is specified, events are published to the tenant configured in the pysysproject.xml file.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`
			:return: The process handle of the simulator process.
			:rtype: L{pysys.process.Process}

			For example::

				# In a 'creator.py' file in test input directory.
				class MyEventCreator(ObjectCreator):
				    def createObject(self, device, time):
				        return {
				                    'time': time,
				                    'type': 'pos_update_event',
				                    'text': 'Position update',
				                    'source': {
				                        'id': device
				                    },
				                    'c8y_Position': {
				                        'lng': random.uniform(0, 10),
				                        'lat': random.uniform(0, 10)
				                    }
				                }
				
				...

				# In the test
				self.startEventSimulator(
				        ['12345'],                  # device IDs
				        1,                          # rate of events to publish
				        f'{self.input}/creator.py', # Python file path
				        'MyEventCreator',           # class name
				        [],                         # constructor parameters for MyEventCreator class
				    )
		"""
		return self._startPublisher(devices, perDeviceRate, '/event/events', creatorFile, creatorClassName, creatorParams, duration, processingMode,tenant=tenant)
	
	def startAlarmSimulator(self, devices, perDeviceRate, creatorFile, creatorClassName, creatorParams, duration=None, processingMode='CEP', tenant=None):
		"""
			Starts an alarm simulator process to publish simulated alarms to Cumulocity IoT.

			The simulator uses an instance of the provided alarm creator class to create new alarms to send, 
			allowing the test to publish alarms of different types.
			The simulator looks up the specified class in the specified Python file and creates a new instance of the class
			using the provided parameters. The alarm creator class must extend the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.

			:param list[str] devices: List of device IDs to generate alarms for.
			:param float perDeviceRate: The rate of alarms to publish per device.
			:param str creatorFile: The path to the Python file containing the alarm creator class.
			:param str creatorClassName: The name of the alarm creator class that extends the :class:`apamax.eplapplications.perf.basetest.ObjectCreator` class.
			:param list creatorParams: The list of parameters to pass to the constructor of the alarm creator class to create a new instance.
			:param str processingMode: Cumulocity IoT processing mode. Possible values are CEP, PERSISTENT, TRANSIENT, and QUIESCENT.
			:param duration: The duration (in seconds) to run the simulator for. If no duration is specified, then the simulator runs until either stopped or the end of the test.
			:type duration: float, optional
			:param tenant: The Cumulocity IoT tenant. If no tenant is specified, alarms are published to the tenant configured in the pysysproject.xml file.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`
			:return: The process handle of the simulator process.
			:rtype: L{pysys.process.Process}

			For example::

				# In a 'creator.py' file in test input directory.
				class MyAlarmCreator(ObjectCreator):
				    def createObject(self, device, time):
				        return {
				                    'source': {
				                        'id': device
				                    },
				                    'type': 'my_alarm',
				                    'text': 'My alarm',
				                    'severity': 'MAJOR',
				                    'status': 'ACTIVE',
				                    'time': time,
				                }
				
				...

				# In the test
				self.startAlarmSimulator(
				        ['12345'],                  # device IDs
				        0.01,                       # rate of alarms to publish
				        f'{self.input}/creator.py', # Python file path
				        'MyAlarmCreator',           # class name
				        [],                         # constructor parameters for MyAlarmCreator class
				    )
		"""
		return self._startPublisher(devices, perDeviceRate, '/alarm/alarms', creatorFile, creatorClassName, creatorParams, duration, processingMode,tenant=tenant)

	def _startPublisher(self, devices, perDeviceRate, resourceUrl, creatorFile, creatorClassName, creatorParams, duration=None, processingMode='CEP',tenant=None):
		"""
			Starts a publisher process to publish simulated data to Cumulocity IoT using provided object creator class.

			:param list[str] devices: List of device IDs.
			:param float perDeviceRate: The rate of objects to publish per device.
			:param str resourceUrl: The resource url, for example /measurement/measurements.
			:param str creatorFile: The path to the Python file containing object creator class.
			:param str creatorClassName: The name of the object creator class.
			:param list creatorParams: The list of parameters to pass to constructor of the object creator class.
			:param str processingMode: Cumulocity IoT processing mode. Possible values are CEP, PERSISTENT, TRANSIENT and QUIESCENT.
			:param duration: The duration (in seconds) to run simulators for. If no duration specified then it runs until either stopped or end of the test.
			:type duration: float, optional
			:param tenant: The Cumulocity IoT tenant. If no tenant is specified, data is published to the tenant configured in the pysysproject.xml file.
			:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`
			:return: The publisher object which can be stopped by calling stop() method on it.
			:rtype: L{pysys.process.Process}
		"""
		tenant = tenant or self.platform.getTenant()
		if not isinstance(devices, list):
			devices = [devices]
		object_creator_info = {
			'className': creatorClassName,
			'constructorParams': creatorParams,
			'file': creatorFile
		}
		env = self.getDefaultEnvirons(command=sys.executable)
		test_framework_root=f'{self.project.EPL_TESTING_SDK}/testframework'
		pythonpath = test_framework_root
		# Add python path from parent
		for d in [env, os.environ]:
			if d.get('PYTHONPATH', '') != '':
				pythonpath = f"{pythonpath}{os.pathsep}{d.get('PYTHONPATH', '')}"

		env['PYTHONPATH'] = pythonpath
		env['PYTHONDONTWRITEBYTECODE'] = 'true'

		(url, username, password) = tenant.url, tenant.username, tenant.password
		script_path = str(pathlib.Path(__file__).parent.joinpath('publisher.py'))
		arguments = [script_path,
			'--base_url', url,
			'--username', username,
			'--password', password,
			'--devices', json.dumps(devices),
			'--per_device_rate', str(perDeviceRate), 
			'--resource_url', resourceUrl,
			'--processing_mode', processingMode,
			'--object_creator_info', json.dumps(object_creator_info),
		]

		if duration is not None:
			arguments.extend(['--duration', str(duration)])

		self.mkdir(f'{self.output}/simulators')
		stdouterr=self.allocateUniqueStdOutErr('simulators/publisher')
		p = self.startPython(arguments, stdouterr=stdouterr, disableCoverage=True, environs=env, background=True)
		self.simulators.setdefault(tenant.getTenantId(), []).append(p)
		self.waitForGrep(stdouterr[0], expr='Started publishing Cumulocity', errorExpr=['ERROR ', 'DataPublisher failed'])
		return p
	
	def _perfMonitorSuffix(self, noSuffixForFirst=True):
		"""
		Gets suffix to add to generated files.

		:param noSuffixForFirst: Do not generate suffix if first perf monitoring thread is running, defaults to True
		:type noSuffixForFirst: bool, optional
		:return: The suffix string.
		:rtype: str
		"""
		if self.perfMonitorCount > 1 or not noSuffixForFirst:
			return '.' + str(self.perfMonitorCount - 1).rjust(2, '0')
		else:
			return ''
	
	def _getEnvironmentDetails(self):
		"""
			Gets environment details in which test is running.

			Used for HTML report.
		"""
		paq_version = self.platform.getC8YConnection().do_get('/service/cep/diagnostics/componentVersion').get('componentVersion', '<unknown>')
		apamaCtrlStatus = self.platform.getC8YConnection().do_get('/service/cep/diagnostics/apamaCtrlStatus')
		microservice_name = apamaCtrlStatus.get('microservice_name', '<unknown>')
		c8y_url = self.platform.getC8YConnection().base_url
		c8y_version = self.platform.getC8YConnection().do_get('/tenant/system/options/system/version').get('value', '<unknown>')
		diagnostic_info = self.platform.getC8YConnection().do_get('/service/cep/diagnostics/info', headers={'Accept':'application/json'})
		pam_version = diagnostic_info.get('productVersion', '<unknown>')
		uptime = diagnostic_info.get('uptime', '<unknown>')
		app_manifest = self.platform.getC8YConnection().do_get(f'/application/applicationsByName/{microservice_name}')
		microservice_resources = app_manifest.get('applications', [{}])[0]['manifest']['resources']
		cpu_limit = microservice_resources['cpu']
		if cpu_limit == '1':
			cpu_limit += ' core'
		else:
			cpu_limit += ' cores'

		env = {
			'Cumulocity IoT Tenant': c8y_url,
			'Cumulocity IoT Version': c8y_version,
			'Microservice name': microservice_name,
			'Microservice CPU Limit': cpu_limit,
			'Microservice Memory Limit': microservice_resources['memory'],
			'Apama Version': f'PAM {pam_version}, PAQ {paq_version}',
		}

		try:
			up = float(uptime)
			uptime = int(up / 1000)
		except Exception:
			pass

		env['Uptime (secs)'] = uptime
		return env

	def startPerformanceMonitoring(self, pollingInterval=2):
		"""
			Starts a performance monitoring thread that periodically gathers and logs various metrics and publishes 
			performance statistics at the end.

			:param pollingInterval: The polling interval to get performance data. Defaults to 2 seconds.
			:type pollingInterval: float, optional
			:return: The background thread.
			:rtype: L{pysys.utils.threadutils.BackgroundThread}
		"""
		if self.perfMonitorThread and self.perfMonitorThread.is_alive():
			self.perfMonitorThread.stop()
			self.perfMonitorThread.join()
		self.perfMonitorCount += 1
		if not os.path.exists(f'{self.output}/{OUTFILE_ENV_DETAILS}.json'):
			self.write_text(f'{self.output}/{OUTFILE_ENV_DETAILS}.json', json.dumps(self._getEnvironmentDetails(), indent=2), encoding='utf8')
		self.perfMonitorThread = self.startBackgroundThread("perf_monitoring_thread", self._monitorPerformance, {'pollingInterval':pollingInterval})
		return self.perfMonitorThread

	def _monitorPerformance(self, stopping, log, pollingInterval):
		"""
			Implements performance gathering thread.
			
			:param stopping: To check if thread should be stopped.
			:param log: The logger.
			:param pollingInterval: The polling interval to get performance data.
		"""
		log.info('Started gathering performance metrics')
		cpu_monitoring_thread = self.startBackgroundThread("cpu_monitoring_thread", self._monitor_cpu_usage_impl)
		suffix = self._perfMonitorSuffix()
		def num(value):
			try:
				f = float(value)
				return f if not math.isnan(f) else 0
			except Exception:
				return 0
		try:
			fieldnames = [PERF_TIMESTAMP, PERF_MEMORY_CORR, PERF_TOTAL_MEMORY_USAGE, PERF_CORR_IQ_SIZE, PERF_CORR_OQ_SIZE, PERF_CORR_SPAW_RATE,
							PERF_CORR_NUM_OUTPUT_SENT, PERF_CORR_NUM_INPUT_RECEIVED]

			if not self.platform.isSmartrulesOnlyMicroservice():
				fieldnames.extend([PERF_MEMORY_APCTRL, PERF_CEP_PROXY_REQ_STARTED, PERF_CEP_PROXY_REQ_COMPLETED, PERF_CEP_PROXY_REQ_FAILED])

			csv_file = open(f'{self.output}/{OUTFILE_PERF_RAW_DATA}{suffix}.csv', 'w', encoding='utf8')
			writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
			writer.writeheader()
			while not stopping.is_set():
				data = {}
				# gather performance data
				# 1) get correlator status
				corr_status = self.platform.getC8YConnection().do_get('/service/cep/diagnostics/correlator/status', headers={'Accept':'application/json'})

				# 2) get apama-ctrl status
				apctrl_status = self.platform.getC8YConnection().do_get('/service/cep/diagnostics/apamaCtrlStatus')

				# write data
				data[PERF_TIMESTAMP] = time.time()
				data[PERF_MEMORY_CORR] = num(corr_status.get('physicalMemoryMB', 0))
				data[PERF_CORR_IQ_SIZE] = num(corr_status.get('numQueuedInput', 0)) # numInputQueuedInput
				data[PERF_CORR_OQ_SIZE] = num(corr_status.get('numOutEventsQueued', 0))
				data[PERF_CORR_NUM_OUTPUT_SENT] = num(corr_status.get('numOutEventsSent', 0))
				data[PERF_CORR_NUM_INPUT_RECEIVED] = num(corr_status.get('numReceived', 0))
				data[PERF_CORR_SPAW_RATE] = num(corr_status.get('swapPagesRead', 0)) + num(corr_status.get('swapPagesWrite', 0))
				data[PERF_TOTAL_MEMORY_USAGE] = data[PERF_MEMORY_CORR]

				if not self.platform.isSmartrulesOnlyMicroservice():
					data[PERF_MEMORY_APCTRL] = num(apctrl_status.get('apama_ctrl_physical_mb', 0))
					data[PERF_TOTAL_MEMORY_USAGE] = data[PERF_MEMORY_CORR] + data[PERF_MEMORY_APCTRL]

					cep_proxy_requests_started = 0
					cep_proxy_requests_completed = 0
					cep_proxy_requests_failed = 0
					cep_proxy_request_counts = apctrl_status.get('cep_proxy_request_counts', {})
					for key in cep_proxy_request_counts.keys():
						cep_proxy_requests_started += num(cep_proxy_request_counts[key].get('requestsStarted', 0))
						cep_proxy_requests_completed += num(cep_proxy_request_counts[key].get('requestsCompleted', 0))
						cep_proxy_requests_failed += num(cep_proxy_request_counts[key].get('requestsFailed', 0))
					data[PERF_CEP_PROXY_REQ_STARTED] = cep_proxy_requests_started
					data[PERF_CEP_PROXY_REQ_COMPLETED] = cep_proxy_requests_completed
					data[PERF_CEP_PROXY_REQ_FAILED] = cep_proxy_requests_failed

				writer.writerow(data)
				csv_file.flush()
				if not stopping.is_set():
					time.sleep(pollingInterval)
		except Exception as ex:
			log.error(f'Exception while gathering performance data: {ex}')
			raise Exception(f'Exception while gathering performance data: {ex}').with_traceback(ex.__traceback__)
		finally:
			if csv_file: csv_file.close()
			cpu_monitoring_thread.stop()
			cpu_monitoring_thread.join()
			self._generatePerfStatistics()
			log.info('Finished performance monitoring')
	
	def _monitor_cpu_usage_impl(self, stopping, log):
		"""
		Implements CPU usage monitoring thread.
		
		:param stopping: To check if thread should be stopped.
		:param log: The logger.
		"""

		url = '/service/cep/diagnostics/cpuUsageMillicores'

		# check if able to monitor CPU usage (REST url exposed + able to calculate CPU usage)
		try:
			cpu_usage = float(self.platform.getC8YConnection().do_get(url + '?sampleDurationMSec=10'))
		except Exception as ex:
			log.info("Unable to monitor CPU usage")
			return

		log.info('Started gathering CPU usage')
		url = url + '?sampleDurationMSec=2000'
		suffix = self._perfMonitorSuffix()
		with open(f'{self.output}/{OUTFILE_PERF_CPU_USAGE}{suffix}.csv', 'w', encoding='utf8') as csv_file:
			writer = csv.DictWriter(csv_file, fieldnames=['timestamp', PERF_CPU_USAGE_MILLI])
			writer.writeheader()
			while not stopping.is_set():
				try:
					cpu_usage = self.platform.getC8YConnection().do_get(url)
					writer.writerow({
						'timestamp': time.time(),
						PERF_CPU_USAGE_MILLI: cpu_usage
						})
					csv_file.flush()
				except Exception as e:
					log.error("Unable to get cpu usage: " + str(e))

	def _generatePerfStatistics(self):
		"""
			Generates performance statistics.
		"""
		suffix = self._perfMonitorSuffix()
		# read data points
		datapoints = {}
		with open(f'{self.output}/{OUTFILE_PERF_RAW_DATA}{suffix}.csv', 'r', encoding='utf8') as csv_file:
			csv_reader = csv.DictReader(csv_file)
			for row in csv_reader:
				all_metrics = [PERF_MEMORY_CORR, PERF_TOTAL_MEMORY_USAGE, PERF_CORR_IQ_SIZE, PERF_CORR_OQ_SIZE, PERF_CORR_SPAW_RATE,
						PERF_CORR_NUM_OUTPUT_SENT, PERF_CORR_NUM_INPUT_RECEIVED]

				if not self.platform.isSmartrulesOnlyMicroservice():
					all_metrics.extend([PERF_MEMORY_APCTRL, PERF_CEP_PROXY_REQ_STARTED,
						PERF_CEP_PROXY_REQ_COMPLETED, PERF_CEP_PROXY_REQ_FAILED])

				for metric_name in all_metrics:
					datapoints.setdefault(metric_name, [])
					datapoints[metric_name].append(float(row[metric_name]))

		cpu_perf_file = f'{self.output}/{OUTFILE_PERF_CPU_USAGE}{suffix}.csv'
		if os.path.exists(cpu_perf_file):
			metric_name = PERF_CPU_USAGE_MILLI
			datapoints.setdefault(metric_name, [])
			with open(cpu_perf_file, 'r', encoding='utf8') as csv_file:
				csv_reader = csv.DictReader(csv_file)
				for row in csv_reader:
					datapoints[metric_name].append(float(row[metric_name]))

		# Extract counter like values to a separate object. We capture difference between first and last value only for these.
		counter_values = {}
		names = [PERF_CORR_NUM_INPUT_RECEIVED, PERF_CORR_NUM_OUTPUT_SENT]

		if not self.platform.isSmartrulesOnlyMicroservice():
			names.extend([PERF_CEP_PROXY_REQ_STARTED, PERF_CEP_PROXY_REQ_COMPLETED, PERF_CEP_PROXY_REQ_FAILED])

		for name in names:
			values = datapoints[name]
			counter_values[name] = int(values[-1]) - int(values[0])
			del datapoints[name]

		self.write_text(f'{OUTFILE_PERF_COUNTERS}{suffix}.json', json.dumps(counter_values, indent=2), encoding='utf8')
		self.write_text(f'{OUTFILE_PERF_RAW_DATA}{suffix}.json', json.dumps(datapoints, indent=2), encoding='utf8')

		def percentile(data, percent): # calculate percentile
			size = len(data)
			return sorted(data)[int(math.ceil((size * percent) / 100)) - 1]
		
		# calculate statistics
		stats = {}
		for name in datapoints.keys():
			values = datapoints[name]
			if len(values) <=0 : continue
			stats[name] = {}
			stats[name]['min'] = min(values)
			stats[name]['max'] = max(values)
			stats[name]['mean'] = statistics.mean(values)
			stats[name]['median'] = statistics.median(values)
			stats[name]['75th_percentile'] =  percentile(values, 75)
			stats[name]['90th_percentile'] =  percentile(values, 90)
			stats[name]['95th_percentile'] =  percentile(values, 95)
			stats[name]['99th_percentile'] = percentile(values, 99)
		
		self.write_text(f'{OUTFILE_PERF_STATS}{suffix}.json', json.dumps(stats, indent=2), encoding='utf8')

		with open(f'{self.output}/{OUTFILE_PERF_STATS}{suffix}.csv', 'w', encoding='utf8') as csv_file:
			# PERF_MEMORY_CORR is present in both apama-ctrl and smartrules. So this works for both without any changes
			columns = ['name'] + list(stats[PERF_MEMORY_CORR].keys())
			writer = csv.DictWriter(csv_file, fieldnames=columns)
			writer.writeheader()

			for name in stats.keys():
				row = {'name':name}
				for col in columns[1:]:
					row[col] = stats[name][col]
				writer.writerow(row)

	def read_json(self, fileName, fileDirectory=None):
		"""
			Reads a JSON file and returns its content.

			:param fileName: Name of the file.
			:type fileName: str
			:param fileDirectory: Directory of the file. Use test output directory if not specified.
			:type fileDirectory: str, optional
			:return: The decoded content of the file.
		"""
		fileDirectory = fileDirectory or self.output
		return json.loads(pathlib.Path(fileDirectory).joinpath(fileName).read_text(encoding='utf8'))

	def _confirmStableQueueSize(self, queue_name, perf_data, noise_floor=200, ratio_threshold=0.5, discard_fraction=0.2):
		"""
			Checks that the queue sizes are stable or coming down. Logs warning if queue sizes are still increasing.

			:param: queue_name: The name of the correlator queue.
			:param: perf_data: The raw performance data.
			:param: noise_floor: Skip analysis if difference between queue sizes at end compared to start is less than this.
			:param: ratio_threshold: Log error if ration of slopes of graph is second half versus first half is more than this.
			:param: discard_fraction: The amount of data to discard at the beginning and the end before performing analysis.
		"""
		values = perf_data['correlator_iq_size' if queue_name == 'input' else 'correlator_oq_size']
		discard_size = int(len(values)*discard_fraction)
		values = values[discard_size:-discard_size]
		if len(values) <= 5:
			self.log.warn('Not enough datapoints to analyse queue growth')
			return

		# Check that queue size graph flattens off, or at least starts to flatten off
		# calculate the segment averages
		left  = values[0 : int(len(values) * 0.35)]
		left  = float(sum(left)) / len(left)
		mid   = values[int(len(values) * 0.35) : int(len(values) * 0.65)]
		mid   = float(sum(mid)) / len(mid)
		right = values[int(len(values) * 0.65) : int(len(values) * 0.95)]
		right = float(sum(right)) / len(right)

		# Easy case - it's going downwards for a large part of the graph, or the change is beneath the noise floor
		if right - left <= noise_floor or right - mid <= noise_floor:
			return
		if mid - left == 0 and right - mid == 0:
			return
		try:
			slope_ratio = (right - mid) / (mid - left)
		except ZeroDivisionError:
			slope_ratio = float("inf")
		
		# if slope is not coming down fast enough then most probably queue is going to get full
		mean_size_towards_end = statistics.mean(values[int(len(values) * 0.85) : int(len(values) * 0.95)])
		if slope_ratio > ratio_threshold:
			self.log.error(f'Correlator {queue_name} queue was increasing continuously. It probably would have been full eventually. Mean queue size towards the end was {mean_size_towards_end}')
		elif slope_ratio > 0.2:
			self.log.warn(f'Correlator {queue_name} queue was increasing slowly. It probably would have been full eventually. Mean queue size towards the end was {mean_size_towards_end}')
		# test is not failed because it might be false positive

	def _to_html_list(self, values):
		"""
		Generates a HTML list to be embedded in an HTML page from provided values.
		"""
		if values is None: return ''
		result = ''
		if isinstance(values, dict):
			for key, value in values.items():
				result += f'<li><span class="key">{key}: </span>{value}</li>'
		elif isinstance(values, list):
			for value in values:
				result += f'<li>{value}</li>'
		else:
			result += f'<li>{str(values)}</li>'
		return f'<ul>{result}</ul>'
	
	def _dict_to_html_table(self, values, column_names):
		"""
		Generates a HTML table to be embedded in an HTML page from provided dictionary.
		:param: values: Dictionary of values.
		:param: column_names: Name of the columns to use.
		"""
		result = '<tr><td>&nbsp;</td>'
		for key in column_names:
			result += f'<th scope="col">{key}</th>'
		result += f'</tr>'

		def format_value(val):
			if isinstance(val, float): return f'{val:0.2f}'
			else: return str(val)

		for metric_name, row in values.items():
			result += f'<tr><th scope="row">{metric_name}</th>'
			if isinstance(row, dict):
				for c in column_names:
					val = row.get(c, '')
					result += f'<td>{format_value(val)}</td>'
			else:
				result += f'<td>{format_value(row)}</td>'
			result += '</tr>'

		return f'<table>{result}</table>'

	def generateHTMLReport(self, description, testConfigurationDetails=None, extraPerformanceMetrics=None):
		"""
		Generates an HTML report of the performance result. The report is generated at the end of the test.

		When testing for multiple variations, multiple HTML reports are combined into a single HTML report.
		
		:param description: A brief description of the test.
		:type description: str
		:param testConfigurationDetails: Details of the test configuration to include in the report.
		:type testConfigurationDetails: dict, list, str, optional
		:param extraPerformanceMetrics: Extra application-specific performance metrics to include in the report.
		:type extraPerformanceMetrics: dict, list, str, optional
		"""
		if self.perfMonitorThread.is_alive():
			self.perfMonitorThread.stop()
			self.perfMonitorThread.join()
		
		suffix = self._perfMonitorSuffix()

		if not os.path.exists(f'{self.output}/{OUTFILE_PERF_STATS}{suffix}.json'):
			self._generatePerfStatistics()

		# method to generate textual representation of a time range
		def format_time_range(timestamp1, timestamp2):
			import datetime
			datetime1 = datetime.datetime.fromtimestamp(timestamp1, datetime.timezone.utc)
			datetime2 = datetime.datetime.fromtimestamp(timestamp2, datetime.timezone.utc)
			
			format1 = datetime1.strftime('%a %Y-%m-%d %H:%M:%S') + ' UTC'
			if datetime1.date()==datetime2.date():
				format2 = datetime2.strftime('%H:%M:%S')
			else:
				format2 = datetime2.strftime('%a %Y-%m-%d %H:%M:%S') + ' UTC'

			delta = datetime2 - datetime1
			delta = delta-datetime.timedelta(microseconds=delta.microseconds)
			return f'{format1} to {format2} (={delta})'
		
		### Now generate codes, html fragments to fill in the template to generate final report

		## Generate HTML for table of standard performance statistics
		# Read statistics in a single dict
		table_data = self.read_json(f'{OUTFILE_PERF_STATS}{suffix}.json')
		# add counter type data to the table as well
		counters = self.read_json(f'{OUTFILE_PERF_COUNTERS}{suffix}.json')
		for s in [PERF_CORR_NUM_INPUT_RECEIVED, PERF_CORR_NUM_OUTPUT_SENT]:
			table_data[s] = counters[s]

		# Extracting the column names. PERF_MEMORY_CORR is present in both apama-ctrl and smartrules. So this
		# works for both without any changes
		column_names = list(table_data[PERF_MEMORY_CORR].keys())

		# prepare dictionary for html using more descriptive names for metrics
		for key in list(METRICS_DESCRIPTION.keys()):
			if key in table_data:
				table_data[METRICS_DESCRIPTION.get(key, key)] = table_data[key]
				del table_data[key]

		standard_perf_stats_table = self._dict_to_html_table(table_data, column_names)

		## Generate HTML list of test configuration
		test_config_list = self._to_html_list(testConfigurationDetails)

		## Generate HTML for any additional performance metrics
		additional_perf_statistics = self._to_html_list(extraPerformanceMetrics)
		if extraPerformanceMetrics:
			additional_perf_statistics = f'<h4>App Specific Performance Statistics</h4>{additional_perf_statistics}'

		## Generate HTML for graphs
		# generate data for memory and queue_size graphs
		queue_data = []
		memory_data = []
		cpu_usage_data = []
		start_time = -1
		end_time = -1
		with open(f'{self.output}/{OUTFILE_PERF_RAW_DATA}{suffix}.csv', 'r', encoding='utf8') as csv_file:
			csv_reader = csv.DictReader(csv_file)
			for row in csv_reader:
				timestamp = float(row[PERF_TIMESTAMP])
				if start_time < 0:
					start_time = timestamp
				end_time = timestamp
				timestamp_milli = 1000.0 * timestamp
				iq = int(float(row[PERF_CORR_IQ_SIZE]))
				oq = int(float(row[PERF_CORR_OQ_SIZE]))
				# generate JavaScript code to create an array of data for a timestamp - [new Date(...), y1_value, y2_value, ...]
				queue_data.append(f'[new Date({timestamp_milli}),{iq}, {oq}]')

				memory = float(row[PERF_MEMORY_CORR])
				if not self.platform.isSmartrulesOnlyMicroservice():
					memory = f'{memory}, {float(row[PERF_MEMORY_APCTRL])}, {float(row[PERF_TOTAL_MEMORY_USAGE])}'

				memory_data.append(f'[new Date({timestamp_milli}), {memory}]')
		queue_time_range = memory_time_range = format_time_range(start_time, end_time)

		# generate data for cpu usage graphs
		if os.path.exists(f'{self.output}/{OUTFILE_PERF_CPU_USAGE}{suffix}.csv'):
			start_time = -1
			end_time = -1
			with open(f'{self.output}/{OUTFILE_PERF_CPU_USAGE}{suffix}.csv', 'r', encoding='utf8') as csv_file:
				csv_reader = csv.DictReader(csv_file)
				for row in csv_reader:
					timestamp = float(row[PERF_TIMESTAMP])
					if start_time < 0:
						start_time = timestamp
					end_time = timestamp
					timestamp_milli = 1000.0 * timestamp
					cpu_usage = float(row[PERF_CPU_USAGE_MILLI])
					cpu_usage_data.append(f'[new Date({timestamp_milli}), {cpu_usage}]')
		cpu_usage_time_range = format_time_range(start_time, end_time)

		memory_labels = '"time", "Correlator (MB)"'
		if not self.platform.isSmartrulesOnlyMicroservice():
			memory_labels = f'{memory_labels}, "Apama Ctrl JVM (MB)", "Total (MB)"'

		### Generate final report.html file by filling in various details into the table
		variation_replacements = {
			'TEST_TITLE': self.descriptor.title,
			'VARIATION_DESCRIPTION': description,
			'VARIATION_TITLE': description,
			'VARIATION_LINKS': '',
			'VARIATION_ID': '0',
			'TEST_CONFIGURATION': test_config_list,
			'STATS_TABLE': standard_perf_stats_table,
			'ADDITIONAL_PERF_STATISTICS': additional_perf_statistics,
			'CORRELATOR_QUEUES_DATA': ','.join(queue_data),
			'CORRELATOR_QUEUES_TIMERANGE': queue_time_range,
			'MEMORY_DATA': ','.join(memory_data),
			'MEMORY_LABELS': memory_labels,
			'MEMORY_TIMERANGE': memory_time_range,
			'CPU_USAGE_DATA': ','.join(cpu_usage_data),
			'CPU_USAGE_TIMERANGE': cpu_usage_time_range,
		}

		self.write_text(f'html_report_data{self._perfMonitorSuffix(False)}.json', json.dumps(variation_replacements, indent=2), encoding='utf8')

	def _generateFinalHTMLReport(self):
		"""
		Generates a final HTML report.

		Combines multiple HTML reports into one.
		"""
		template_dir = f'{self.project.EPL_TESTING_SDK}/testframework/resources'
		variation_template = pathlib.Path(f'{template_dir}/template_perf_details.html').read_text(encoding='utf8')

		files = glob.glob(f'{self.output}/html_report_data*.json')
		files = sorted(files)

		variation_htmls = []
		variation_links = []
		env_details = self.read_json(f'{OUTFILE_ENV_DETAILS}.json')

		memory_limit_val = env_details['Microservice Memory Limit']
		memory_numeric = float(''.join(filter(str.isdigit, memory_limit_val)))
		memory_unit = ''.join(filter(str.isalpha, memory_limit_val))

		if memory_unit == 'Ti':
			memory_limit_mb = f'"valueRange": [0, {memory_numeric * 1024 * 1024}]'
		elif memory_unit == 'Gi':
			memory_limit_mb = f'"valueRange": [0, {memory_numeric * 1024}]'
		elif memory_unit == 'Mi':
			memory_limit_mb = f'"valueRange": [0, {memory_numeric}]'
		else:
			memory_limit_mb = f'"includeZero": true'

		cpu_limit_millis = float(env_details['Microservice CPU Limit'].split(' ')[0])
		cpu_limit_millis = f'"valueRange": [0, {cpu_limit_millis * 1000}]'

		for i,f in enumerate(files):
			f = f.strip()
			filename = os.path.basename(f)			
			replacements = self.read_json(filename)
			variation_desc = replacements['VARIATION_DESCRIPTION']
			replacements['VARIATION_ID'] = f'variation_{i}'
			replacements['VARIATION_TITLE'] = variation_desc
			replacements['CPU_RANGE'] = cpu_limit_millis
			replacements['MEMORY_RANGE'] = memory_limit_mb

			variation_html = variation_template
			for (key, value) in replacements.items():
				variation_html = variation_html.replace(f'@{key}@', value)
			if i > 0:
				variation_html = '<br/><a class="backtotoplink" href="#top_of_the_page">Back to top</a><br/><hr/>' + variation_html
			variation_htmls.append(variation_html)
			variation_links.append(f'<a href="#test_variation_variation_{i}">{variation_desc}</a>')
		
		if len(files) > 1:
			if 'Uptime (secs)' in env_details:
				# don't need to log uptime in combined report
				del env_details['Uptime (secs)']

		variation_links_html = '' if len(variation_links) <= 1 else f'<h2>Variation List</h2>{self._to_html_list(variation_links)}'

		replacements = {
			'TEST_TITLE': self.descriptor.title,
			'ENVIRONMENT_DETAILS': self._to_html_list(env_details),
			'VARIATION_DATA': '\n\n'.join(variation_htmls),
			'VARIATION_LINKS': variation_links_html,
		}

		self.copyWithReplace(f'{template_dir}/template_perf_report.html', f'{self.output}/report.html', replacements, marker='@')
		self.log.info(f'Generated performance report {os.path.abspath(os.path.join(self.output, f"report.html"))}')

	def validate(self):
		"""
			Performs standard validations of the test run.

			The following validations are performed.

			- No errors in the microservice log.
			- Microservice did not terminate because of high memory usage.
			- Microservice's memory usage remained below 90% of available memory.
			- Correlator was not swapping memory.

			The test should define its own `validate` method for performing any application-specific validation. Ensure that
			the test calls the super implementation of the `validate` method, using `super(PySysTest, self).validate()`.
		"""
		logFile = self.platform.getApamaLogFile()

		self.assertGrep(logFile, expr=' (ERROR|FATAL) .*', contains=False)

		# Check that microservice did not use more than 90% of available memory
		self.assertGrep(logFile, expr='apama_highmemoryusage.*Apama is using 90. of available memory', contains=False)
		
		# Check that microservice did not exit because of high memory usage
		self.assertGrep(logFile, expr='(Java exit 137|exit code 137)', contains=False)

		# Check that no request to /cep from cumulocity failed
		if not self.platform.isSmartrulesOnlyMicroservice():
			for file in glob.glob(f'{self.output}/{OUTFILE_PERF_COUNTERS}*.json'):
				perf_counters = self.read_json(file)
				self.assertThat('num_failed_cep_requests == 0', num_failed_cep_requests=perf_counters[PERF_CEP_PROXY_REQ_FAILED])

		# Check that correlator was not swapping
		for file in glob.glob(f'{self.output}/{OUTFILE_PERF_STATS}*.json'):
			perf_stats = self.read_json(file)
			self.assertThat('correlator_swap_read_write == 0', correlator_swap_read_write=perf_stats[PERF_CORR_SPAW_RATE]['min'])

			# check that mean and median size of input and output queue are reasonable
			filename = os.path.basename(file).replace(OUTFILE_PERF_STATS, OUTFILE_PERF_RAW_DATA)
			raw_perf_data = self.read_json(f'{self.output}/{filename}')
			for (queue, max_size) in [('input', 20_000), ('output', 10_000)]:
				stats = perf_stats[PERF_CORR_IQ_SIZE if queue == 'input' else PERF_CORR_OQ_SIZE]
				self.assertThat('median_queue_size < max_queue_size * 0.8', median_queue_size=stats['median'], max_queue_size=max_size)
				self.assertThat('mean_queue_size < max_queue_size * 0.8', mean_queue_size=stats['mean'], max_queue_size=max_size)
				self._confirmStableQueueSize(queue, raw_perf_data)

class EPLAppsPerfTest(ApamaC8YPerfBaseTest):
	"""
	Base class for EPL applications performance tests.

	The class :class:`ApamaC8YPerfBaseTest` supersedes this class and should be used when writing new tests.
	"""
