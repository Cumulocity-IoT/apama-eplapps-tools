## License
# Copyright (c) 2020 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import json
import os
import urllib
import codecs
from pathlib import Path


class EPLApps:
	"""Class for interacting with Apama EPL Apps in Cumulocity

		:param connection: A C8yConnection object for the connection to the platform.
	"""

	def __init__(self, connection):
		self.connection = connection

	def deploy(self, file, name='', description=None, inactive=False, redeploy=False):
		"""
		Deploys a local mon file to Apama EPL Apps in Cumulocity.

		:param file: Path to local mon file to be deployed as an EPL app
		:param name: Name of the EPL app to be uploaded (optional). By default this will be the name of the mon file being uploaded.
		:param description: Description of the EPL app (optional)
		:param inactive: Boolean of whether the app should be 'active' (inactive=False) or 'inactive' (inactive=True) when it is deployed.
		:param redeploy: Boolean of whether we are overwriting an existing EPL app.
		"""
		active = not inactive
		# Check EPL file specified is valid .mon file:
		if not os.path.exists(file):
			raise FileNotFoundError(f'Deploy failed. File \'{file}\' not found.')
		elif os.path.splitext(file)[1] != '.mon':
			raise TypeError(f'Deploy failed. \'{file}\' is not a valid .mon file.')
		# Check whether EPL app of that name already exists for tenant:
		try:
			existingEPLApps = self.getEPLApps()
		except Exception as err:
			raise OSError(f'Could not deploy EPL app. {err}')
		existingAppNames = [app['name'] for app in existingEPLApps]
		# If name option not specified, use name of the .mon file specified by default
		if name == '':
			# Removing file path (directories) up to name of file:
			filename = os.path.basename(file)
			name = filename[:filename.rfind('.mon')]
		if name in existingAppNames:
			if redeploy:
				try:
					updateArgs = {'file': file}
					if description is not None: updateArgs['description'] = description
					updateArgs['state'] = 'active' if active else 'inactive'
					self.update(name, **updateArgs)
					return
				except Exception as err:
					raise OSError(f'Unable to redeploy EPL app \'{name}\'. {err}')
			else:
				raise FileExistsError(f'Deploy failed. \'{name}\' already exists in Apama EPL Apps.')
		try:
			file_contents = self.__read_text_withBOM(file)
		except Exception as err:
			raise IOError(f"Deploy failed. {err}")
		try:
			body = {
				'name': name,
				'description': description or '',
				'state': 'active' if active else 'inactive',
				'contents': file_contents
			}
			responseBytes = self.connection.do_request_json('POST', '/service/cep/eplfiles', body, useLocationHeaderPostResp=False)
			response = json.loads(responseBytes)

			if active and len(response['errors']) > 0:
				self.delete(name)
				errorStrings = []
				for error in response['errors']:
					errorStrings.append(f"[{os.path.basename(file)}:{error['line']}] {error['text']}")
				raise ValueError('\n'.join(errorStrings))
		except Exception as err:
			raise OSError(f'Unable to deploy EPL app \'{name}\' using POST on {self.connection.base_url}/service/cep/eplfiles.\n{err}')


	def update(self, name, new_name=None, file=None, description=None, state=None):
		"""
		Updates an EPL app in Cumulocity.

		:param name: name of the EPL App to be updated.
		:param new_name: the updated name of the EPL app (optional)
		:param file: path to the local mon file containing the updated contents of the EPL app (optional)
		:param description: the updated description of the EPL app (optional)
		:param state: the updated state of the EPL app (optional)
		"""
		if new_name is None and file is None and description is None and state is None:
			raise ValueError(f"Update failed. Please specify at least 1 field to update.")
		try:
			appId = self.getAppId(name)
		except FileNotFoundError as err:
			raise FileNotFoundError(f'Update failed. {err}')
		except Exception as err:
			raise OSError(f'Update failed. {err}')

		body = {}
		if new_name is not None:
			body['name'] = new_name
		if description is not None:
			body['description'] = description

		if state is not None:
			if state.lower() in ('active', 'inactive'):
				body['state'] = state.lower()
			else:
				raise ValueError(f'Update failed. Invalid argument, \'{state}\', specified for the --state option. State can either be \'active\' or \'inactive\'.')

		if file is not None:
			# Check file is valid:
			if not os.path.exists(file):
				raise FileNotFoundError(f'Update failed. File \'{file}\' not found.')
			elif os.path.splitext(file)[1] != '.mon':
				raise TypeError(f'Update failed. \'{file}\' is not a valid .mon file.')
			try:
				contents = self.__read_text_withBOM(file)
			except Exception as err:
				raise IOError(f"Update failed. {err}")
			body['contents'] = contents
		try:
			responseBytes = self.connection.do_request_json('PUT', f'/service/cep/eplfiles/{appId}', body)
			response = json.loads(responseBytes)

			if len(response['errors']) > 0:
				errorStrings = []
				for error in response['errors']:
					errorStrings.append(f"[{response['name']}:{error['line']}] {error['text']}")
				raise ValueError('\n'.join(errorStrings))
		except Exception as err:
			raise ConnectionError(f'Unable to update EPL app \'{name}\' using PUT on {self.connection.base_url}/service/cep/eplfiles/{appId}.\n{err}')


	def getAppId(self, appName: str, jsonEPLAppsList=None):
		"""
		Gets the id of EPL app for a given EPL app name. If no EPL app with appname exists, an exception is raised.

		:param appName: The name of the EPL app we wish to get the id of
		:param jsonEPLAppsList: A json collection of EPL apps
		:return: The id of the EPL app
		"""
		jsonEPLAppsList = jsonEPLAppsList or self.getEPLApps()
		for app in jsonEPLAppsList:
			if app['name'] == appName:
				return app['id']
		raise FileNotFoundError(f'EPL app \'{appName}\' not found.')

	def getEPLApps(self, includeContents=False):
		"""
		:param includeContents: Fetches the EPL files with their contents if True. This is an optional query parameter.
		:return: A json object of all the user's EPL apps in Cumulocity
		"""
		try:
			return self.connection.do_get(f'/service/cep/eplfiles?contents={includeContents}')['eplfiles']
		except Exception as err:
			raise OSError(f'GET on {self.connection.base_url}/service/cep/eplfiles failed. {err}')

	def delete(self, name: str):
		"""
		Deletes an EPL app in Cumulocity.

		:param name: The name of the EPL app to be deleted.
		"""
		try:
			appId = self.getAppId(name)
		except FileNotFoundError as err:
			raise FileNotFoundError(f'Delete failed. {err}')
		except Exception as err:
			raise OSError(f'Delete failed. GET on {self.connection.base_url}/service/cep/eplfiles failed. {err}')
		try:
			self.connection.request('DELETE', f'/service/cep/eplfiles/{appId}')
		except Exception as err:
			raise OSError(f'Unable to delete EPL app \'{name}\' using DELETE on {self.connection.base_url}/service/cep/eplfiles. {err}')
	
	def __read_text_withBOM(self, path):
		"""
		Thin wrapper for Path(<path>).read_text() . It assumes the file is UTF-8 encoded if it starts with the UTF-8 BOM, despite the current locale.
		This method is used internally to make the tool behave consistently with many text editors and IDEs on Windows, which also honour the UTF-8 BOM.
		Such a file is rendered correctly, therefore it should also be deployed correctly, else user expectations are confounded.

		:param path: The path to extract the text from
		"""
		if Path(path).read_bytes().startswith(codecs.BOM_UTF8):
			return Path(path).read_text(encoding="utf8")
		else:
			return Path(path).read_text()
