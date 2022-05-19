## License
# Copyright (c) 2020 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import time, math
from datetime import date, datetime
import os 
from .connection import C8yConnection

class CumulocityPlatform(object):
	"""
	Class to create a connection to the Cumulocity IoT platform configured in pysysproject.xml
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

		(url, self._remoteTenantId, username, password) = self.getC8yConnectionDetails()
		self.parent.log.info(f"Connecting to Cumulocity platform at {url} as user {username}")
		self._c8yConn = C8yConnection(url, username, password)
		self.parent.addCleanupFunction(self.shutdown)

		if not self._remoteTenantId:
			self._remoteTenantId = self._c8yConn.do_get('/tenant/currentTenant')['name']

		self._applicationId = None
		self._instanceName = None
		applications = self._c8yConn.do_get("/application/applications?pageSize=2000")["applications"]
		for application in applications:
			if 'contextPath' in application and application['contextPath'].lower() == 'cep':
				self._applicationId = application['id']
				instances = {}
				try:
					while len(instances) == 0:
						res = self._c8yConn.do_get("/inventory/managedObjects?type=c8y_Application_%s" % self._applicationId)
						if len(res["managedObjects"]) == 0:
							break # this means we got the wrong one
						instances = res["managedObjects"][0]["c8y_Subscriptions"][self._remoteTenantId]["instances"].keys()
						time.sleep(1.0)
					if len(instances) > 0:
						self._instanceName = list(instances)[0]
						break
				except Exception as e:
					self.parent.log.debug("Caught exception looking for platform subscription. Assuming that means it's a different application: %s" % e)

		if not self._instanceName or not self._applicationId:
			raise Exception("Could not find the apama-ctrl service running in your tenant")
			
		self.parent.startBackgroundThread("spooling", self._logSpoolingThread)
		self.parent.waitForGrep('platform.log', expr='.')

	def _logSpoolingThread(self, stopping, log):
		""" When doing non-local testing, this method implements a thread that is responsible for regularly grabbing
			the latest microservice log snippets, and writing it to a single appending log file """
		self.__spoolLogs = True

		logLineDeduplication = set()
		nowtime = time.time()
		now = datetime.fromtimestamp(nowtime);
		utc_offset = (datetime.fromtimestamp(nowtime) - datetime.utcfromtimestamp(nowtime)).total_seconds()
		off_hours = math.floor(utc_offset/3600)
		off_minutes = math.floor((utc_offset%3600)/60)

		startdate = now.strftime("%Y-%m-%dT%H:%M:%S")+'%2B'+("{:02}".format(off_hours))+":"+("{:02}".format(off_minutes))
		while self.__spoolLogs and not stopping.is_set():
			time.sleep(2.0)
			try:
				resp = self._c8yConn.do_get("/application/applications/%s/logs/%s?dateFrom=%s&dateTo=2099-01-01T00:00:00%%2B01:00" % (self._applicationId, self._instanceName, startdate), jsonResp=False)
				logLatest = resp.decode('utf8').split("\n")

				with open(os.path.join(self.parent.output, 'platform.log'), 'a', encoding='utf8') as logfile:
					for line in logLatest:
						if line not in logLineDeduplication:
							logfile.write(line + "\n")
					logLineDeduplication = logLineDeduplication.union(logLatest)
			except Exception as e:
				log.error("Exception while spooling logs:" + str(e))

	def shutdown(self):
		""" Stop spooling the log files when the test finishes. """
		self.__spoolLogs = False

	def getC8YConnection(self):
		""" Return the C8yConnection object for this platform. """
		return self._c8yConn

	def getApamaLogFile(self):
		""" Return the path to the Apama log file within Cumulocity IoT."""
		return os.path.join(self.parent.output, 'platform.log')
