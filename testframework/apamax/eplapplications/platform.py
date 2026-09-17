## License
# Copyright (c) 2020-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import time, math, threading, os, urllib, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from .tenant import CumulocityTenant

#: Timeout (in seconds) for each socket operation when requesting the microservice log, so that a stalled request
#: does not stop that thread noticing it has been asked to stop. Bounds each operation, not the whole request.
LOG_SPOOLING_REQUEST_TIMEOUT_SECS = 10

#: How long (in seconds) the log spooling thread waits between requests for the microservice log.
LOG_SPOOLING_POLL_INTERVAL_SECS = 1.0

#: How far back (in seconds) each log request overlaps the previous one, to cover the lag before a logged line
#: becomes queryable. Duplicates only cost bandwidth; anything below the lag is lost for good.
LOG_SPOOLING_WINDOW_OVERLAP_SECS = 10

#: How far back (in seconds) before spooling started the window may reach, allowing for the platform's clock being
#: behind ours. Kept small, as anything here risks collecting the tail of a previous test's log.
LOG_SPOOLING_START_SKEW_ALLOWANCE_SECS = 1.0

#: How many consecutive failed log requests before looking for the instance that replaced the one we are on.
LOG_SPOOLING_FAILURES_BEFORE_REDISCOVERY = 5

#: HTTP statuses meaning an application is not one whose log we could spool, rather than a transient problem.
_NOT_OUR_APPLICATION_STATUSES = (401, 403, 404)

class CumulocityPlatform(object):
	"""
	Class to create a connection to the Cumulocity platform configured in pysysproject.xml
	and spool the logs from the platform locally.

	Requires the following properties to be set in pysysproject.xml:
		* CUMULOCITY_SERVER_URL
		* CUMULOCITY_TENANT
		* CUMULOCITY_USERNAME
		* CUMULOCITY_PASSWORD

	For use with the EPLApps class for uploading EPL applications:
		self.platform = CumulocityPlatform(self)
		eplapps = EPLApps(self.platform.getC8YConnection())
		eplapps.deploy(self.input+'/test.mon', activate=True)
		self.waitForGrep(self.platform.getApamaLogFile(), expr='Added monitor eplfiles.test')
	
	:param parent: The PySys test object using this platform object.
	"""

	def getC8yConnectionDetails(self):
		"""
			Return the (url, tenantid, username, password) defined in the pysysproject.xml)
		"""
		return (self.parent.project.CUMULOCITY_SERVER_URL,
				self.parent.project.CUMULOCITY_USERNAME.split('/')[0] if '/' in self.parent.project.CUMULOCITY_USERNAME else None,
				self.parent.project.CUMULOCITY_USERNAME,
				self.parent.project.CUMULOCITY_PASSWORD)

	def __init__(self, parent):

		self.parent=parent

		(url, self._remoteTenantId, self.username, self.password) = self.getC8yConnectionDetails()
		self.parent.log.info(f"Connecting to Cumulocity platform at {url} as user {self.username}")

		self._tenant = CumulocityTenant(url, self.username, self.password, self._remoteTenantId)
		self._c8yConn = self._tenant.getConnection()
		try:
			platform_version = self._c8yConn.do_get('/service/cep/diagnostics/componentVersion')['releaseTrainVersion']
			# Check that this is not a legacy/non-CD version. Example: Older / non-CD versions has a version number like 10.18.0, 10.16.0 .., 
			# where as CD versions usually start with 2 digit year number, example: 24.0.0
			if platform_version.startswith("10."):
				self.parent.log.warning("It is recommended to use the \'main\' branch for the current release or switch to the appropriate branch for Long-term support or Maintenance releases.")
		except Exception as e:
			self.parent.log.warning("Could not get the platform version to check version information - is apama-ctrl subscribed?")

		self.parent.addCleanupFunction(self.shutdown)
		if not self._remoteTenantId: self._remoteTenantId = self._tenant.getTenantId()

		""" All tenants that can be used for testing """
		self.__subscribedTenants = []

		""" Protects initialisation and mutation of __subscribedTenants """
		self.__lock = threading.Lock()

		self._applicationId = None
		self._instanceName = None
		self._isMultiTenantMicroservice = False
		self._microserviceName = ''
		self.__applicationOwnerTenantId = self._remoteTenantId

		applications = self._c8yConn.do_get("/application/applications?pageSize=2000")["applications"]
		
		for application in applications:
			if 'contextPath' in application and application['contextPath'].lower() == 'cep':
				self._applicationId = application['id']
				self._isMultiTenantMicroservice = application.get('manifest',{}).get('isolation', '') == 'MULTI_TENANT'
				self._microserviceName = application['name']
				self.__applicationOwnerTenantId = application.get('owner',{}).get('tenant',{}).get('id')

				self._instanceName = self._findRunningInstance(self._applicationId)
				if self._instanceName: break

		self.isBootstrapTenant = True
		# This means that the tenant is not the bootstrap tenant for the multi-tenant microservice.
		if self._isMultiTenantMicroservice and self.__applicationOwnerTenantId != self._remoteTenantId:
			self.isBootstrapTenant = False
   
		# self._instanceName used for log spooling only. so validate for isBootstrapTenant
		if (self.isBootstrapTenant and not self._instanceName) or not self._applicationId:
			raise Exception("Could not find the apama-ctrl service running in your tenant")

		# The log spooling must be done only for the bootstrap tenant in case of multi-tenant microservice.
		if self.isBootstrapTenant:
			self.parent.log.info(f"Spooling the log of microservice {self._microserviceName} instance {self._instanceName} to platform.log")
			# Create the file up front, so that waiters have something to wait on even if the first requests fail
			open(os.path.join(self.parent.output, 'platform.log'), 'w', encoding='utf8').close()
			self.parent.startBackgroundThread("spooling", self._logSpoolingThread)
			self.parent.waitForGrep('platform.log', expr='.', timeout=self._defaultTimeoutSecs(),
				detailMessage=f'waiting for the log of {self._microserviceName} instance {self._instanceName}')

	def _defaultTimeoutSecs(self):
		"""
		The PySys signal timeout. Imported here, not at module scope, so this module stays importable without
		PySys - the eplapp command line tool pulls it in and does not require PySys.

		:meta private:
		"""
		from pysys.constants import TIMEOUTS
		return TIMEOUTS['WaitForSignal']

	def _findRunningInstance(self, applicationId, timeoutSecs=None):
		"""
		Find the name of the instance (a Kubernetes pod) to spool the microservice log from.

		Waits for exactly one instance: a starting microservice reports none, a restarting one briefly reports two.
		Falls back to the first of several rather than giving up.

		:param applicationId: The id of the application to find a running instance of.
		:param timeoutSecs: How long to keep retrying for, defaulting to the PySys signal timeout. Pass 0 for a
			single attempt.
		:return: The instance name, or None if this is not an application we can spool, or none was found in time.

		:meta private:
		"""
		if timeoutSecs is None: timeoutSecs = self._defaultTimeoutSecs()
		deadline = time.time() + timeoutSecs
		instances = {}
		while True:
			try:
				# Asking for a refresh is necessary to get an up to date list of instances
				applicationStatus = self._c8yConn.do_get(f"/application/applications/{applicationId}/status?refresh=true",
					timeoutSecs=LOG_SPOOLING_REQUEST_TIMEOUT_SECS)
				# A status without instances races with the microservice starting up, so treat it as "none yet"
				instances = (applicationStatus or {}).get('c8y_Status', {}).get('instances', None) or {}
			except urllib.error.HTTPError as e:
				if e.code in _NOT_OUR_APPLICATION_STATUSES:
					# Most likely a different application sharing the 'cep' context path, or we are a subtenant
					self.parent.log.debug(f"Cannot see the status of application {applicationId} ({e}), assuming it is not the microservice under test")
					return None
				self.parent.log.debug(f"Failed to get the status of application {applicationId}, will retry: {e}")
			except Exception as e:
				# Anything else is transient, so keep trying until the deadline
				self.parent.log.debug(f"Failed to get the status of application {applicationId}, will retry: {e}")

			if len(instances) == 1:
				return list(instances)[0]

			if time.time() >= deadline:
				if len(instances) > 1:
					# Better a log that may stop partway through the test than no log at all
					self.parent.log.warning(f"Application {applicationId} reports more than one running instance ({sorted(instances)}), spooling the log of the first")
					return list(instances)[0]
				if timeoutSecs > 0:
					self.parent.log.warning(f"Application {applicationId} did not report a running instance within {timeoutSecs} seconds")
				return None

			if len(instances) > 1:
				# Picking the instance on its way out would give a log that stops partway through the test
				self.parent.log.debug(f"Application {applicationId} reports more than one running instance ({sorted(instances)}), waiting for a single instance")
			time.sleep(1.0)

	def _logSpoolingThread(self, stopping, log):
		""" When doing non-local testing, this method implements a thread that is responsible for regularly grabbing
			the latest microservice log snippets, and writing it to a single appending log file """
		self.__spoolLogs = True

		logLineDeduplication = set()
		# Ask only for what is new each time; requesting the whole log grows every request until the endpoint
		# times out on it, after which no more log arrives
		earliestLogTime = datetime.now(timezone.utc) - timedelta(seconds=LOG_SPOOLING_START_SKEW_ALLOWANCE_SECS)
		getLogsFrom = earliestLogTime
		consecutiveFailures = 0

		while self.__spoolLogs and not stopping.is_set():
			try:
				requestStart = datetime.now(timezone.utc)
				dateRange = urllib.parse.urlencode({'dateFrom': getLogsFrom.isoformat(timespec='milliseconds')})
				resp = self._c8yConn.do_get("/application/applications/%s/logs/%s?%s" % (self._applicationId, self._instanceName, dateRange), jsonResp=False,
					timeoutSecs=LOG_SPOOLING_REQUEST_TIMEOUT_SECS)
				consecutiveFailures = 0
				logLatest = resp.decode('utf8').split("\n")

				# The endpoint returns nothing at all while a container is starting, so don't move past a window
				# until something arrives
				if logLatest != ['']:
					with open(os.path.join(self.parent.output, 'platform.log'), 'a', encoding='utf8') as logfile:
						for line in logLatest:
							if line not in logLineDeduplication:
								logfile.write(line + "\n")
								logLineDeduplication.add(line)
					# Never reach back before spooling started, or the overlap would collect a previous test's log
					getLogsFrom = max(requestStart - timedelta(seconds=LOG_SPOOLING_WINDOW_OVERLAP_SECS), earliestLogTime)
			except Exception as e:
				# Requests that are interrupted or time out while the test is finishing are expected, so don't
				# report those as errors
				if self.__spoolLogs and not stopping.is_set():
					log.error("Exception while spooling logs:" + str(e))
					consecutiveFailures += 1
					if consecutiveFailures >= LOG_SPOOLING_FAILURES_BEFORE_REDISCOVERY:
						# A rescheduled microservice comes back under a new instance name. Don't wait for one here,
						# or this thread stops noticing it has been asked to stop
						consecutiveFailures = 0
						instanceName = self._findRunningInstance(self._applicationId, timeoutSecs=0)
						if instanceName and instanceName != self._instanceName:
							log.info(f"Microservice instance changed from {self._instanceName} to {instanceName}, spooling the log of the new instance")
							self._instanceName = instanceName

			# Wait before the next request, waking up immediately if this thread has been asked to stop. As well as
			# avoiding needless load on the platform, this keeps the thread responsive to being stopped at the end of
			# the test, since each request opens a new connection and so cannot be interrupted once it is under way
			if stopping.wait(LOG_SPOOLING_POLL_INTERVAL_SECS): break

	def shutdown(self):
		""" Stop spooling the log files when the test finishes. """
		self.__spoolLogs = False

	def getC8YConnection(self):
		""" Return the C8yConnection object for this platform. """
		return self._c8yConn

	def getApamaLogFile(self):
		""" Return the path to the Apama log file within Cumulocity."""
		return os.path.join(self.parent.output, 'platform.log')

	def getMicroserviceName(self):
		""" Get the name of the Apama-ctrl microservice being tested. """
		return self._microserviceName

	# Check if microservice supports EPL apps (undocumented)
	def supportsEPLApps(self):
		return not ('apama-ctrl-smartrules' in self.getMicroserviceName())

	# Check if microservice is smartrules-only microservice (undocumented)
	def isSmartrulesOnlyMicroservice(self):
		return 'apama-ctrl-smartrules' in self.getMicroserviceName()

	# Check if microservice is multi-tenant (undocumented)
	def isMultiTenantMicroservice(self):
		return self._isMultiTenantMicroservice

	def getTenant(self):
		"""
		Get the Cumulocity tenant configured in the pysysproject.xml file.
		:return: The Cumulocity tenant.
		:rtype: :class:`~apamax.eplapplications.tenant.CumulocityTenant`
		"""
		return self._tenant

	def getSubscribedTenants(self):
		"""
		Get list of Cumulocity tenants subscribed to the Apama-ctrl microservice if testing against a
		multi-tenant Apama-ctrl microservice.

		If the Apama-ctrl microservice is per-tenant, it returns a list only containing the configured tenant.

		:return: List of Cumulocity tenants.
		:rtype: list[:class:`~apamax.eplapplications.tenant.CumulocityTenant`]
		"""
		if not self._isMultiTenantMicroservice:
			return [self.getTenant()]

		PAGE_SIZE = 100  # By default, pageSize = 5 for querying to C8y
		
		def create_url(**params):
			return f'/tenant/tenants?withApps=false&{urllib.parse.urlencode(params)}'

		with self.__lock:

			if len(self.__subscribedTenants) > 0:
				return self.__subscribedTenants

			# The configured tenant is subscribed
			self.__subscribedTenants.append(self.getTenant())

			try:
				resp = self._c8yConn.do_get(create_url(withTotalPages=True,pageSize=PAGE_SIZE,currentPage=1),jsonResp=True)
			except:
				# Expected to raise an 403 forbidden error if tenant does not have any subtenants.
				return self.__subscribedTenants

			subTenants = []

			if isinstance(resp, dict) and 'tenants' in resp and len(resp['tenants']) > 0:
				subTenants += resp['tenants']
				
				TOTAL_PAGES = 1
				# Make sure we retrieve all pages from query
				if 'statistics' in resp and "totalPages" in resp['statistics']:
					TOTAL_PAGES = resp['statistics']['totalPages']

				if TOTAL_PAGES > 1:
					for currentPage in range(2, TOTAL_PAGES + 1):
						try:
							resp = self._c8yConn.do_get(create_url(pageSize=PAGE_SIZE, currentPage=currentPage),jsonResp=True)
						except: pass
						
						if isinstance(resp, dict) and 'tenants' in resp and len(resp['tenants']) > 0:
							subTenants += resp['tenants']
			
			for tenant in subTenants:
				if 'applications' in tenant and 'references' in tenant['applications']:
					applications = tenant['applications']['references']
					for app in applications:
						if self._applicationId == app['application']['id']:
							username = (tenant["id"] + '/' + self.username.split('/')[1]) if '/' in self.username else self.username
							self.__subscribedTenants.append(CumulocityTenant(tenant["domain"], username, self.password, tenant["id"]))

			return self.__subscribedTenants
