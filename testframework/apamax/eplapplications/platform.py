## License
# Copyright (c) 2020-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import time, math, threading, os, urllib, urllib.parse
from datetime import datetime, timezone, timedelta
from .tenant import CumulocityTenant

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

				instances = {}
				try:
					while len(instances) == 0:
						applicationStatus = self._c8yConn.do_get(f"/application/applications/{self._applicationId}/status?refresh=true")
						instances = applicationStatus['c8y_Status']['instances']
						time.sleep(1.0)
					if len(instances) > 0:
						self._instanceName = list(instances)[0]
						break
				except Exception as e:
					self.parent.log.debug("Caught exception looking for platform subscription. Assuming that means it's a different application: %s" % e)

		self.isBootstrapTenant = True
		# This means that the tenant is not the bootstrap tenant for the multi-tenant microservice.
		if self._isMultiTenantMicroservice and self.__applicationOwnerTenantId != self._remoteTenantId:
			self.isBootstrapTenant = False
   
		# self._instanceName used for log spooling only. so validate for isBootstrapTenant
		if (self.isBootstrapTenant and not self._instanceName) or not self._applicationId:
			raise Exception("Could not find the apama-ctrl service running in your tenant")

		# The log spooling must be done only for the bootstrap tenant in case of multi-tenant microservice.
		if self.isBootstrapTenant:
			self.parent.startBackgroundThread("spooling", self._logSpoolingThread)
			self.parent.waitForGrep('platform.log', expr='.')

	def _logSpoolingThread(self, stopping, log):
		""" When doing non-local testing, this method implements a thread that is responsible for regularly grabbing
			the latest microservice log snippets, and writing it to a single appending log file """
		self.__spoolLogs = True

		logLineDeduplication = set()
		now = datetime.now(timezone.utc)
		dateRange = urllib.parse.urlencode({
			'dateFrom': now.isoformat(timespec='milliseconds'),
			'dateTo': (now + timedelta(days=365)).isoformat(timespec='milliseconds')
		})

		while self.__spoolLogs and not stopping.is_set():
			try:
				resp = self._c8yConn.do_get("/application/applications/%s/logs/%s?%s" % (self._applicationId, self._instanceName, dateRange), jsonResp=False)
				logLatest = resp.decode('utf8').split("\n")

				with open(os.path.join(self.parent.output, 'platform.log'), 'a', encoding='utf8') as logfile:
					for line in logLatest:
						if line not in logLineDeduplication:
							logfile.write(line + "\n")
							logLineDeduplication.add(line)
			except Exception as e:
				log.error("Exception while spooling logs:" + str(e))

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
