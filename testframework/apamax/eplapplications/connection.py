## License
# Copyright (c) 2020-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import urllib, ssl, json, urllib.request, base64, logging

class C8yConnection(object):
	"""
	Simple object to create connection to Cumulocity and perform REST requests.

	:param url: The Cumulocity tenant url.
	:param username: The username.
	:param password: The password.
	:param timeoutSecs: The default timeout (in seconds) for each socket operation performed while making a
		REST request using this connection. Individual requests can override this. If neither is specified,
		Python's default socket timeout applies.
	"""

	def __init__(self, url, username, password, timeoutSecs=None):
		if not (url.startswith('http://') or url.startswith('https://')):
			url = 'https://' + url
		auth_handler = urllib.request.HTTPBasicAuthHandler()
		auth_handler.add_password(realm='Name of Your Realm', uri=url, user=username, passwd=password)
		auth_handler.add_password(realm='Cumulocity', uri=url, user=username, passwd=password)
		self.urlopener = urllib.request.build_opener(urllib.request.HTTPSHandler(), auth_handler)
		self.base_url = url
		self.auth_header = "Basic " + base64.b64encode(bytes("%s:%s" % (username, password), "utf8")).decode()
		self.timeoutSecs = timeoutSecs
		self.logger = logging.getLogger("pysys.apamax.eplapplications.C8yConnection")

	def request(self, method, path, body=None, headers=None, useLocationHeaderPostResp=True, timeoutSecs=None):
		"""
		Perform an HTTP request. In case of POST request, return the id of the created resource.

		:param method: The method.
		:param path: The path of the resource.
		:param body: The body for the request.
		:param headers: The headers for the request.
		:param useLocationHeaderPostResp: Whether or not to attempt to use the
			'Location' header in the response to return the ID of the resource that was created by a POST request.
		:param timeoutSecs: The timeout (in seconds) for each socket operation performed while making this request.
			If not specified, the default timeout of this connection is used, if it has one.
		:return: Body of the response. In case of POST request, id of the resource specified by the Location header.
		"""
		headers = headers or {}
		headers['Authorization'] = self.auth_header
		if isinstance(body, str):
			body = bytes(body, encoding='utf8')
		url = self.base_url[:-1] if self.base_url.endswith('/') else self.base_url
		req = urllib.request.Request(url + path, data=body, headers=headers, method=method)
		# Only pass a timeout if one was requested, so that by default urllib's own behaviour (i.e. Python's
		# default socket timeout) is left untouched
		timeoutSecs = timeoutSecs if timeoutSecs is not None else self.timeoutSecs
		resp = self.urlopener.open(req, **({'timeout': timeoutSecs} if timeoutSecs is not None else {}))

		if resp.getheader('Content-Type',
								'') == 'text/html':  # we never ask for HTML, if we got it, this is probably the wrong URL (or we're very confused)
			raise Exception(
				f'Failed to perform REST request for resource {path} on url {self.base_url}. Verify that the base Cumulocity URL is correct.')

		if useLocationHeaderPostResp and method == 'POST':
			# Attempt to use location header to return the ID of the resource
			loc = resp.getheader('Location', '')
			if loc.endswith('/'):
				loc = loc[:-1]
			return loc.split('/')[-1]
		return resp.read()

	def do_get(self, path, params=None, headers=None, jsonResp=True, timeoutSecs=None):
		"""
		Perform GET request.

		:param path: The path to the resource.
		:param params: The query params.
		:param headers: The headers.
		:param jsonResp: Response is JSON.
		:param timeoutSecs: The timeout (in seconds) for each socket operation performed while making this request.
			If not specified, the default timeout of this connection is used, if it has one.
		:return: The body of the response. If JSON output is expected then parse the JSON string to python object.
		"""
		if params:
			path = f'{path}?{urllib.parse.urlencode(params)}'
		body = self.request('GET', path, None, headers, timeoutSecs=timeoutSecs)
		if body and jsonResp:
			body = json.loads(body)
		return body

	def do_request_json(self, method, path, body, headers=None, **kwargs):
		"""
		Perform REST request (POST/GET mainly) with JSON body.

		:param method: The REST method.
		:param path: The path to resource.
		:param body: The JSON body.
		:param headers: The headers.
		:param kwargs: Any additional kwargs to pass to the `request` method.
		:return: Response body string.
		"""
		headers = headers or {}
		headers['Content-Type'] = 'application/json'
		headers["Accept"] = 'application/json'
		body = json.dumps(body)
		return self.request(method, path, body, headers, **kwargs)
