## License
# Copyright (c) 2023 Software AG, Darmstadt, Germany and/or its licensors

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


class AnalyticsBuilder:
	"""Class for interacting with Apama Analytics Builder Models in Cumulocity IoT.

		:param connection: A C8yConnection object for the connection to the platform.
	"""

	def __init__(self, connection):
		self.connection = connection

	def deploy(self, file, redeploy=False):
		"""
		Deploys a local json file to Apama Analytics Builder in Cumulocity IoT.

		:param file: Path to local json file to be deployed as an Analytics Builder model.
		:param redeploy: Boolean of whether we are overwriting an existing EPL app.
		"""
		# Check file specified is valid file:
		if not os.path.exists(file):
			raise FileNotFoundError(f'Deploy failed. File \'{file}\' not found.')
		elif os.path.splitext(file)[1] != '.json':
			raise TypeError(f'Deploy failed. \'{file}\' is not a valid .json file.')
		# Check whether model of that name already exists for tenant:
		try:
			existingModels = self.getModels()
		except Exception as err:
			raise OSError(f'Could not deploy Analytics Builder model. {err}')
		existingModelNames = [model['name'] for model in existingModels]
		try:
			file_contents = self.__read_text_withBOM(file)
		except Exception as err:
			raise IOError(f"Deploy failed. {err}")
		model = json.loads(file_contents)
		name =  model['name']
		if name in existingModelNames:
			if redeploy:
				try:
					updateArgs = {'file': file}
					self.update(name, **updateArgs)
					return
				except Exception as err:
					raise OSError(f'Unable to redeploy Analytics Builder model \'{name}\'. {err}')
			else:
				raise FileExistsError(f'Deploy failed. \'{name}\' already exists in Analytics Builder.')
		try:
			responseBytes = self.connection.do_request_json('POST', '/service/cep/analyticsbuilder', model, useLocationHeaderPostResp=False)
			response = json.loads(responseBytes)
			if len(response['runtimeError']) > 0:
				self.delete(name)
				raise ValueError(response['runtimeError'])
		except Exception as err:
			raise OSError(f'Unable to deploy Analytics Builder model \'{name}\' using POST on {self.connection.base_url}/service/cep/analyticsbuilder.\n{err}')


	def update(self, name, new_name=None, file=None, description=None, mode=None, state=None):
		"""
		Updates an Analytics Builder model in Cumulocity IoT.

		:param name: name of the Analytics Builder model to be updated.
		:param new_name: the updated name of the Analytics Builder model (optional)
		:param file: path to the local json file containing the updated contents of the Analytics Builder model (optional)
		:param description: the updated description of the Analytics Builder model (optional)
		:param state: the updated state of the Analytics Builder model (optional)
		"""
		if new_name is None and file is None and description is None and mode is None and state is None:
			raise ValueError(f"Update failed. Please specify at least 1 field to update.")
		try:
			body = self.getModel(name)
			modelId = body['id']
		except FileNotFoundError as err:
			raise FileNotFoundError(f'Update failed. {err}')
		except Exception as err:
			raise OSError(f'Update failed. {err}')

		if file is not None:
			# Check file is valid:
			if not os.path.exists(file):
				raise FileNotFoundError(f'Update failed. File \'{file}\' not found.')
			elif os.path.splitext(file)[1] != '.json':
				raise TypeError(f'Update failed. \'{file}\' is not a valid .json file.')
			try:
				body = json.loads(self.__read_text_withBOM(file))
			except Exception as err:
				raise IOError(f"Update failed. {err}")

		if new_name is not None:
			body['name'] = new_name
		if description is not None:
			body['description'] = description

		if mode is not None:
			if mode.lower() in ('draft','production','simulation','test'):
				body['mode'] = mode.upper()
			else:
				raise ValueError(f'Update failed. Invalid argument, \'{mode}\', specified for the --mode option. Mode can be one of draft/production/simulation/test')

		if state is not None:
			if state.lower() in ('active', 'inactive'):
				body['state'] = state.upper()
			else:
				raise ValueError(f'Update failed. Invalid argument, \'{state}\', specified for the --state option. State can either be \'active\' or \'inactive\'.')
		try:
			responseBytes = self.connection.do_request_json('PUT', f'/service/cep/analyticsbuilder/{modelId}', body)
			response = json.loads(responseBytes)

			if len(response['runtimeError']) > 0:
				self.delete(name)
				raise ValueError(response['runtimeError'])
		except Exception as err:
			raise ConnectionError(f'Unable to update Analytics Builder model \'{name}\' using PUT on {self.connection.base_url}/service/cep/analyticsbuilder/{modelId}.\n{err}')

	def getModel(self, modelName: str, jsonModelList=None):
		"""
		Gets the content of an Analytics Builder model for a given name. If no model with name exists, an exception is raised.

		:param modelName: The name of the Analytics Builder model we wish to get the id of
		:param jsonModelList: A json collection of Analytics Builder Models
		:return: The id of the Analytics Builder Model
		"""
		jsonModelList = jsonModelList or self.getModels()
		for model in jsonModelList:
			if model['name'] == modelName:
				return model
		raise FileNotFoundError(f'Analytics Builder model \'{modelName}\' not found.')


	def getModelId(self, modelName: str, jsonModelList=None):
		"""
		Gets the id of an Analytics Builder model for a given name. If no model with name exists, an exception is raised.

		:param modelName: The name of the Analytics Builder model we wish to get the id of
		:param jsonModelList: A json collection of Analytics Builder Models
		:return: The id of the Analytics Builder Model
		"""
		jsonModelList = jsonModelList or self.getModels()
		for model in jsonModelList:
			if model['name'] == modelName:
				return model['id']
		raise FileNotFoundError(f'Analytics Builder model \'{modelName}\' not found.')

	def getModels(self):
		"""
		Gets all Analytics Builder models from the tenant 
		:return: A json object of all the user's Analytics Builder models in Cumulocity IoT.
		"""
		try:
			return self.connection.do_get(f'/service/cep/analyticsbuilder')['analyticsBuilderModelRepresentations']
		except Exception as err:
			raise OSError(f'GET on {self.connection.base_url}/service/cep/analyticsbuilder failed. {err}')

	def delete(self, name: str):
		"""
		Deletes an Analytics Builder model in Cumulocity IoT.

		:param name: The name of the Analytics Builder model to be deleted.
		"""
		try:
			modelId = self.getModelId(name)
		except FileNotFoundError as err:
			raise FileNotFoundError(f'Delete failed. {err}')
		except Exception as err:
			raise OSError(f'Delete failed. GET on {self.connection.base_url}/service/cep/analyticsbuilder failed. {err}')
		try:
			self.connection.request('DELETE', f'/service/cep/analyticsbuilder/{modelId}')
		except Exception as err:
			raise OSError(f'Unable to delete Analytics Builder model \'{name}\' using DELETE on {self.connection.base_url}/service/cep/analyticsbuilder. {err}')
	
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
