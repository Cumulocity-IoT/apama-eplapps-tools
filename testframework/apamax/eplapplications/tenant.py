## License
# Copyright (c) 2022 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from .connection import C8yConnection

class CumulocityTenant(object):

	"""
	Class to represent a Cumulocity IoT tenant. 

	It is used to get a `~apamax.eplapplications.connection.C8yConnection` object to perform a REST request against the tenant.

	:param url: The Cumulocity IoT tenant URL.
	:param username: The username.
	:param password: The password.
	:param tenantId: The optional tenant ID. If not provided, it is fetched from the Cumulocity IoT tenant.

	"""

	def __init__(self, url, username, password, tenantId=None):
		self.url = url
		self.username = username
		self.password = password
		self.tenantId = tenantId
		self.connection = C8yConnection(self.url, self.username, self.password)

		if not self.tenantId:
			self.tenantId = self.connection.do_get('/tenant/currentTenant')['name']

	def getConnection(self):
		"""
		Returns the connection object to the tenant.

		:return: The connection object to the tenant.
		:rtype: :class:`~apamax.eplapplications.connection.C8yConnection`
		"""
		return self.connection

	def getTenantId(self):
		""" Get the tenant ID. """
		return self.tenantId

	# Forward the request call to the connection object.
	def request(self, *args, **kwargs):
		return self.connection.request(*args, **kwargs)

	# Forward the do_get call to connection object.
	def do_get(self,*args, **kwargs):
		return self.connection.do_get(*args, **kwargs)

	# Forward the do_request_json call to connection object.
	def do_request_json(self,*args, **kwargs):
		return self.connection.do_request_json(*args, **kwargs)
