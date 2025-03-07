## License
# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import json

# Constants for smart rule types
RULE_ON_ALARM_SEND_SMS = 'onAlarmSendSms'
RULE_ON_ALARM_SEND_EMAIL = 'onAlarmSendEmail'
RULE_ON_ALARM_ESCALATE = 'onAlarmEscalateAlarm'
RULE_INCREASE_ALARM_SEVERITY = 'onAlarmDurationIncreaseAlarmSeverity'
RULE_ON_GEOFENCE_CREATE_ALARM = 'onGeofenceCreateAlarm'
RULE_ON_GEOFENCE_SEND_EMAIL = 'onGeofenceSendEmail'
RULE_CALCULATE_ENERGY = 'calculateEnergyConsumption'
RULE_MISSING_MEASUREMENTS = 'onMissingMeasurementsCreateAlarm'
RULE_ON_ALARM_EXECUTE_OPERATION = 'onAlarmExecuteOperation'
RULE_EXPLICIT_THRESHOLD = 'explicitThresholdSmartRule'
RULE_THRESHOLD = 'thresholdSmartRule'

RULE_NAMES = {
	RULE_ON_ALARM_SEND_SMS: 'When alarm is received then SMS is sent',
	RULE_ON_ALARM_SEND_EMAIL: 'When alarm is received then email is sent',
	RULE_ON_ALARM_ESCALATE: 'Escalate alarm',
	RULE_INCREASE_ALARM_SEVERITY: 'Increase alarm severity when active for too long',
	RULE_ON_GEOFENCE_CREATE_ALARM: 'On geofence create alarm',
	RULE_ON_GEOFENCE_SEND_EMAIL: 'On geofence send email',
	RULE_CALCULATE_ENERGY: 'Calculates energy consumption',
	RULE_MISSING_MEASUREMENTS: 'Creates alarm when measurements are missing',
	RULE_ON_ALARM_EXECUTE_OPERATION: 'Executes an operation when alarm is received',
	RULE_EXPLICIT_THRESHOLD: 'Create alarm when measurement reaches explicit thresholds',
	RULE_THRESHOLD: 'Creates alarms when measurement reaches thresholds',
}

class SmartRule(object):
	"""
		Class representing a smart rule object.

		An instance of this class must be created by calling the appropriate build method of 
		the class :class:`SmartRulesManager`.

		Call the `deploy` method to deploy a smart rule to Cumulocity IoT and call the `delete` 
		method on a previously deployed smart rule to delete it from Cumulocity IoT.
		
		Any updates to the object are not deployed on Cumulocity IoT until the `deploy` method is called.
	"""
	NAME_PREFIX = 'PYSYS_'

	def __init__(self, ruleType, configuration, smartRulesManager):
		self.ruleType = ruleType						# Name of the smart rule template
		self.ruleName = None							# Name of the smart rule - set below
		self.configuration = configuration or {}		# Smart rule configuration
		self.enabledSources = None						# List of device IDs for which smart rule should be enabled
		self.disabledSources = None						# List of device IDs for which smart rule should be enabled
		self.enabled = True								# Whether the smart rule should be enabled
		self.managedObjectId = None						# The ID of the managed object for a local smart rule
		self.connection = smartRulesManager.connection	# The connection object
		self.log = smartRulesManager.log				# The logger object
		self._id = None									# ID of the smart rule managed object.
		self._cepModuleId = None						# Internal ID of the smart rule.
		self._roleScope = None							# Rule is 'global' or 'local'
		self.setRuleName(RULE_NAMES.get(ruleType, ruleType))

	def getID(self):
		"""
		Get the ID of the smart rule.

		Returns None if the smart rule is deleted or not yet deployed.

		:return: ID of the smart rule.
		:rtype: str
		"""
		return self._id

	def getRuleName(self):
		"""
		Get the name of the smart rule.

		:return: The name of the smart rule.
		:rtype: str
		"""
		return self.ruleName

	def setRuleName(self, name, addTestPrefix=True):
		"""
		Set the name of the smart rule.
		
		:param str name: The name.
		:param  bool addTestPrefix: Add a test prefix to the name of the smart rule so that it can be identified and cleaned up as part of the test setup.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		if addTestPrefix:
			name = SmartRule.NAME_PREFIX + name
		self.ruleName = name
		return self

	def isGlobal(self):
		"""
		Check if the smart rule is global.

		:return: `True` if the smart rule is global, `False` otherwise.
		:rtype: bool
		"""
		return (self._roleScope == 'global') or (self.managedObjectId is None)

	def setGlobal(self):
		"""
		Set the smart rule to be global.

		If a smart rule is previously set to be local to a device or group, it cannot be changed to be global.

		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		if self._roleScope == 'local' or (self.managedObjectId is not None):
			raise Exception('The smart rule cannot be marked global as it is already marked local.')
		self.managedObjectId = None
		self._roleScope = 'global'
		return self

	def isLocal(self):
		"""
		Check if the smart rule is local to a device or a group.

		:return: `True` if the smart rule is local to a device or a group, `False` otherwise.
		:rtype: bool
		"""
		return not self.isGlobal()

	def setLocal(self, deviceOrGroupId):
		"""
		Set the smart rule to be local to the specified device or group.

		If a smart rule is previously set to be global, it cannot be changed to be local to a device or group.

		:param str deviceOrGroupId: The ID of the device or group.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		if self._roleScope == 'global':
			raise Exception('The smart rule cannot be marked local as it is already marked global.')

		if (self.managedObjectId is not None) and (self.managedObjectId != deviceOrGroupId):
			raise Exception(f'The smart rule cannot be marked local as it is already marked local for device {self.managedObjectId}.')

		if deviceOrGroupId is None:
			raise Exception('The specified device or group cannot be None.')

		self.managedObjectId = deviceOrGroupId if isinstance(deviceOrGroupId, str) else deviceOrGroupId['id']
		self._roleScope = 'local'
		return self

	def getConfiguration(self):
		"""
		Get the configuration of the smart rule instance.

		:return: The configuration.
		:rtype: dict
		"""
		return self.configuration

	def updateConfiguration(self, configuration):
		"""
		Update the configuration of the smart rule instance.

		:param dict[str,any] configuration: A dictionary of the updated configuration values.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		self.configuration.update(configuration)
		return self

	def getEnabledSources(self):
		"""
		Get the list of device IDs for which this smart rule is enabled.

		The list will be empty for a global smart rule that is enabled for all devices.

		:return: The list of device IDs.
		:rtype: list
		"""
		return self.enabledSources

	def setEnabledSources(self, deviceList):
		"""
		Set the list of device IDs for which this smart rule must be enabled.

		If the smart rule is local to a group, all devices must be part of the group.

		:param str deviceList: The list of devices or device IDs.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		self.enabledSources = self._toDeviceIds(deviceList)
		return self

	def getDisabledSources(self):
		"""
		Get the list of device IDs for which this smart rule is disabled.

		:return: The list of device IDs.
		:rtype: list
		"""
		return self.disabledSources

	def setDisabledSources(self, deviceList):
		"""
		Set the list of device IDs for which this smart rule must be disabled.

		The disabled sources list will be ignored if the enabled sources list is also set.

		:param list deviceList: The list of devices or device IDs.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		self.disabledSources = self._toDeviceIds(deviceList)
		return self

	def isEnabled(self):
		"""
		Check if the smart rule is enabled.

		:return: `True` if the smart rule is enabled, `False` otherwise.
		:rtype: bool
		"""
		return self.enabled

	def setEnabled(self, enabled=True):
		"""
		Enable or disable the smart rule.

		:param bool enabled: The smart rule is enabled if `True`, otherwise it is disabled.
		:return: The updated smart rule object.
		:rtype: :class:`SmartRule`
		"""
		self.enabled = enabled
		return self

	def deploy(self, **kwargs):
		"""
		Deploy the smart rule to Cumulocity IoT.
		"""
		if self._id is None and self._cepModuleId is None:
			# create smart rule
			self._createRule(**kwargs)
		else:
			self._updateRule(**kwargs)

	def delete(self, **kwargs):
		"""
		Delete the smart rule from Cumulocity IoT.
		"""
		if self._id is None or self._cepModuleId is None:
			raise Exception(f'Trying to delete previously deleted or not yet deployed {self._getDesc()}')
		try:
			self.connection.request("DELETE", self._getEndPoint(), **kwargs)
			# Reset the IDs so that if deploy is called on this object, we create new smart rule instance.
			self._resetIds()
			self.log.debug(f'Deleted {self._getDesc()}')
		except Exception as err:
			raise Exception(f'Failed to delete {self._getDesc()} using DELETE on {self.connection.base_url}{self._getEndPoint()}: {err}')
	
	def _getDesc(self):
		"""
		Get the description of the smart rule for logging.

		:return: A basic description of the smart rule.
		:rtype: str
		"""
		attrs = {
			'type':self.ruleType
		}
		if self._id is not None:
			attrs['ruleId'] = self._id
		
		attrs_str = ', '.join([f'{k}={v}' for (k,v) in attrs.items()])
		ruleContext = 'global' if self.isGlobal() else 'local'
		return f"{ruleContext} smart rule '{self.ruleName}' ({attrs_str})"

	def _createRule(self, **kwargs):
		""" Create the smart rule on Cumulocity IoT. """
		self._resetIds()
		body = self._getRequestBody()
		try:
			self._getEndPoint()
			resp = self.connection.do_request_json("POST", self._getEndPoint(), body=body, useLocationHeaderPostResp=False, **kwargs)
			resp = json.loads(resp)
			self._extractAndSaveIds(resp)
			self.log.debug(f'Created {self._getDesc()}')
		except Exception as err:
			raise Exception(f'Failed to create {self._getDesc()} using POST on {self.connection.base_url}{self._getEndPoint()}: {err}')
	
	def _updateRule(self, **kwargs):
		""" Update the smart rule on Cumulocity IoT. """
		body = self._getRequestBody()
		# c8y doesn't like if type is sent when updating a rule
		if 'type' in body: body.pop('type')
		if 'cepModuleId' in body: body.pop('cepModuleId')
		try:
			resp = self.connection.do_request_json("PUT", self._getEndPoint(), body=body, **kwargs)
			resp = json.loads(resp)
			self._extractAndSaveIds(resp)
			self.log.debug(f'Updated {self._getDesc()}')
		except Exception as err:
			raise Exception(f'Failed to update {self._getDesc()} using PUT on {self.connection.base_url}{self._getEndPoint()}: {err}')

	@staticmethod
	def _toDeviceIds(deviceList):
		""" 
		Extract the device IDs from the list of the devices. 
		
		:param deviceList: Device(s).
		:type deviceList: str, dict, or list
		:return: List of device IDs.
		:rtype: list[str]
		"""

		if deviceList is None: return None

		result = []
		deviceList = deviceList or []
		if isinstance(deviceList, (str, dict)):
			deviceList = [deviceList]
		for device in deviceList:
			# This can either be the id or a ManagedObject
			id = device if isinstance(device, str) else device['id']
			if id:
				result.append(str(id))

		return result

	def _getRequestBody(self):
		"""
		Get the body of the smart rule used for creating/updating a smart rule using the REST API.

		:return: a dictionary containing all the data required to create/update the smart rule using REST API.
		:rtype: dict
		"""
		request = {
			'ruleTemplateName': self.ruleType,
			'name': self.ruleName,
			'config': self.configuration,
			'enabled': self.enabled,
		}

		if self.isLocal():
			request['c8y_Context'] = {'id':self.managedObjectId, 'context': 'device'}
			request['enabledSources'] = (self.getEnabledSources() or [])
		else:
			# Set either enabledSources or disabledSources. If enabledSources is set, ignore the disabledSources.
			if self.getEnabledSources() is not None:
				request['enabledSources'] = self.getEnabledSources()
			else:
				request['disabledSources'] = (self.getDisabledSources() or [])
		return request

	def _extractAndSaveIds(self, response):
		"""
		Extract the ID and cepModuleId of the smart rule and save them.

		These are created by Cumulocity IoT when a smart rule is successfully created.

		:param dict response: The response from Cumulocity IoT.
		"""
		self._id = response['id']
		self._cepModuleId = response['cepModuleId']

	def _resetIds(self):
		"""
		Reset the id and cepModuleId of the smart rule.
		"""
		self._id = None
		self._cepModuleId = None

	def _getEndPoint(self):
		"""
		Gets the REST endpoint associated with the smart rule.

		:return: The REST endpoint of the smart rule.
		:rtype: str
		"""
		return '/service/smartrule' + ( '/managedObjects/%s' % self.managedObjectId if self.managedObjectId is not None else '') + '/smartrules' + ('/%s' % self._id if self._id is not None else '')

	def _isTestSmartRule(self):
		"""
		Checks if the smart rule was created by the test framework as part of a test.

		:return: `True` if the smartRule was created by the framework, `False` otherwise.
		:rtype: bool
		"""
		return self.ruleName.startswith(SmartRule.NAME_PREFIX)

class SmartRulesManager(object):
	"""
	Class responsible for building smart rules objects that can be deployed on Cumulocity IoT.
	
	See the methods in the :class:`SmartRule` class to customize a smart rule object and deploy it.

	:param tenant: The Cumulocity IoT tenant.
	:type tenant: :class:`~apamax.eplapplications.tenant.CumulocityTenant`.
	:param log: The `logger` instance to use for logging.
	"""

	def __init__(self, tenant, log):
		self.connection = tenant.getConnection()
		self.log = log

	def getAllSmartRules(self, withLocalRules=False):
		"""
		Get all smart rules deployed on Cumulocity IoT.

		:param withLocalRules: If `True`, also include smart rules local to a device or group.
		:return: List of smart rule objects.
		:rtype: list[:class:`SmartRule`]
		"""
		withLocalRules = 'true' if withLocalRules else 'false'
		response = self.connection.request('GET', f'/service/smartrule/smartrules?withPrivateRules={withLocalRules}')
		rules = json.loads(response)['rules']
		return [self._parseSmartRule(rule) for rule in rules]

	def build_onMeasurementExplicitThresholdCreateAlarm(self, fragment, series, rangeMin=90, rangeMax=100, alarmType='c8y_ThresholdAlarm', alarmText='Threshold exceeded'):
		"""
		Build a smart rule object for the rule "On measurement explicit threshold create alarm".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param str fragment: Measurement fragment the smart rule listens for.
		:param str series: Measurement series the smart rule listens for.
		:param float rangeMin: The minimum value of measurements for which an alarm is raised.
		:param float rangeMax: The maximum value of measurements for which an alarm is raised.
		:param str alarmType: The type of raised alarms.
		:param str alarmText: The alarm message.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'explicit': True,
			'fragment': fragment,
			'series': series,
			'redRangeMin': rangeMin,
			'redRangeMax': rangeMax,
			'alarmType': alarmType,
			'alarmText': alarmText,
		}
		return SmartRule(RULE_EXPLICIT_THRESHOLD, config, self)

	def build_onGeofenceCreateAlarm(self, geofence, triggerAlarmOn='leaving', alarmType='c8y_GeofenceAlarm', alarmSeverity='MAJOR', alarmText='Geofence violation'):
		"""
		Build a smart rule object for the rule "On geofence create alarm".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param list[dict] geofence: The polygon that defines the boundaries of a region. It should be a list of dictionaries containing "lng" and "lat" keys.
		:param str triggerAlarmOn: The reason for triggering the alarm - one of "entering", "leaving", or "both". The default is "leaving".
		:param str alarmType: The type of raised alarms.
		:param str alarmSeverity: The severity of raised alarms.
		:param str alarmText: The alarm message.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		#triggerAlarmOn can be 'both', 'entering' and 'leaving'
		config = {
			'geofence': geofence,
			'triggerAlarmOn': triggerAlarmOn,
			'alarmType': alarmType,
			'alarmSeverity': alarmSeverity,
			'alarmText': alarmText,
		}

		return SmartRule(RULE_ON_GEOFENCE_CREATE_ALARM, config, self)

	def build_onMissingMeasurementsCreateAlarm(self, measurementType, timeIntervalMinutes=60, alarmType='c8y_MissingMeasurementsAlarm', alarmSeverity='MAJOR', alarmText='Missing measurements of type: #{type}'):
		"""
		Build a smart rule object for the rule "On missing measurements create alarm".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param str measurementType: The type of measurement.
		:param float timeIntervalMinutes: Time (in minutes) to wait for missing measurements.
		:param str alarmType: The type of raised alarms.
		:param str alarmSeverity: The severity of raised alarms.
		:param str alarmText: The alarm message.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'measurementType': measurementType,
			'timePeriod': timeIntervalMinutes,
			'alarmType': alarmType,
			'alarmSeverity': alarmSeverity,
			'alarmText': alarmText,
		}
		return SmartRule(RULE_MISSING_MEASUREMENTS, config, self)

	def build_onAlarmSendSMS(self, alarmTypes, smsTo, smsText='Alarm occurred'):
		"""
		Build a smart rule object for the rule "On alarm send SMS".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param alarmTypes: The types of alarms that trigger the rule.
		:type alarmTypes: str or list[str]
		:param str smsTo: The target phone number for the SMS.
		:param str smsText: The text of the SMS.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'alarmType': self._seq_to_str(alarmTypes),
			'to': smsTo,
			'text': smsText,
		}
		return SmartRule(RULE_ON_ALARM_SEND_SMS, config, self)

	def build_onAlarmSendEmail(self, alarmTypes, sendTo, sendCC=None, sendBCC=None, replyTo=None,
			subject='New #{severity} alarm from #{source.name}',
			message='New #{severity} alarm has been received from #{source.name}. Alarm text is: "#{text}".'):
		"""
		Build a smart rule object for the rule "On alarm send email".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param alarmTypes: The types of alarms that trigger the rule.
		:type alarmTypes: str or list[str]
		:param str sendTo: The recipients of the email.
		:param sendCC: The recipients that are to receive a copy of the email.
		:type sendCC: str, optional
		:param sendBCC: The recipients that are to receive a blind copy of the email.
		:type sendBCC: str, optional
		:param replyTo: The reply-to address for the email.
		:type replyTo: str, optional
		:param str subject: The subject of the email.
		:param str message: The text of the email.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'alarmType': self._seq_to_str(alarmTypes),
			'to': sendTo,
			'cc': sendCC,
			'bcc': sendBCC,
			'replyTo': replyTo,
			'subject': subject,
			'text': message,
		}
		return SmartRule(RULE_ON_ALARM_SEND_EMAIL, config, self)

	def build_onAlarmEscalateStepSendEmail(self, sendTo, sendCC=None, sendBCC=None, replyTo=None,
			subject='New #{severity} alarm from #{source.name}',
			message='New #{severity} alarm has been received from #{source.name}. Alarm text is: "#{text}".'):
		"""
		Build an escalation step to send an email for the rule "On alarm escalate it".

		:param str sendTo: The recipients of the email.
		:param sendCC: The recipients that are to receive a copy of the email.
		:type sendCC: str, optional
		:param sendBCC: The recipients that are to receive a blind copy of the email.
		:type sendBCC: str, optional
		:param replyTo: The reply-to address for the email.
		:type replyTo: str, optional
		:param str subject: The subject of the email.
		:param str message: The text of the email.
		:return: An escalation step object.
		"""
		return self.build_onAlarmSendEmail(alarmTypes='todo', sendTo=sendTo, sendCC=sendCC, sendBCC=sendBCC,
			replyTo=replyTo, subject=subject, message=message)

	def build_onAlarmEscalateStepSendSMS(self, smsTo, smsText='New #{severity} alarm has been received from #{source.name}. Alarm text is: "#{text}".'):
		"""
		Build an escalation step to send an SMS for the rule "On alarm escalate it".

		:param str smsTo: The target phone number for the SMS.
		:param str smsText: The text of the SMS.
		:return: An escalation step object.
		"""
		return self.build_onAlarmSendSMS(alarmTypes='todo', smsTo=smsTo,smsText=smsText)

	def build_onAlarmEscalateIt(self, alarmTypes, escalationSteps):
		"""
		Build a smart rule object for the rule "On alarm escalate it".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		Call the `build_onAlarmEscalateStepSendEmail` or `build_onAlarmEscalateStepSendSMS` methods to create escalation steps.

		:param alarmTypes: The types of alarms that trigger the rule.
		:type alarmTypes: str or list[str]
		:param list escalationSteps: Escalation steps.
		:return:
		:rtype: :class:`SmartRule`
		"""

		sub_rules = []
		for step in escalationSteps:
			if not isinstance(step, SmartRule):
				raise Exception(f'Invalid escalation step provided: {step}')
			config = step.getConfiguration().copy()
			config['ruleTemplateName'] = step.ruleType
			config['alarmType'] = self._seq_to_str(alarmTypes)
			sub_rules.append(config)

		return SmartRule(RULE_ON_ALARM_ESCALATE, smartRulesManager=self, configuration={
			'alarmType': self._seq_to_str(alarmTypes),
			'subrules': sub_rules,
		})

	def build_onAlarmDurationIncreaseSeverity(self, alarmTypes, alarmDurationMinutes=1.0):
		"""
		Build a smart rule object for the rule "On alarm duration increase severity".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.
		
		:param alarmTypes: The types of alarms that trigger the rule.
		:type alarmTypes: str or list[str]
		:param float alarmDurationMinutes: The duration (in minutes) an alarm must be active before increasing the severity.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'alarmType': self._seq_to_str(alarmTypes),
			'duration': alarmDurationMinutes * 60.0,
		}
		return SmartRule(RULE_INCREASE_ALARM_SEVERITY, config, self)

	def build_onGeofenceSendEmail(self, geofence, sendTo, sendCC=None, sendBCC=None, replyTo=None,
			subject='New geofence violation from #{source.name}', message='New geofence violation from #{source.name}'):
		"""
		Build a smart rule object for the rule "On geofence send email".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param list[dict] geofence: The polygon that defines the boundaries of a region. It should be a list of dictionaries containing "lng" and "lat" keys.
		:param str sendTo: The recipients of the email.
		:param sendCC: The recipients that are to receive a copy of the email.
		:type sendCC: str, optional
		:param sendBCC: The recipients that are to receive a blind copy of the email.
		:type sendBCC: str, optional
		:param replyTo: The reply-to address for the email.
		:type replyTo: str, optional
		:param str subject: The subject of the email.
		:param str message: The text of the email.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'geofence': geofence,
			'to': sendTo,
			'cc': sendCC,
			'bcc': sendBCC,
			'replyTo': replyTo,
			'subject': subject,
			'text': message,
		}
		return SmartRule(RULE_ON_GEOFENCE_SEND_EMAIL, config, self)

	def build_calculateEnergyConsumption(self, inputFragment='c8y_EnergyCounter', inputSeries='E', timeIntervalMinutes=1.0, outputFragment='c8y_EnergyConsumption', outputSeries='E'):
		"""
		Build a smart rule object for the rule "Calculate energy consumption".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param str inputFragment: The name of the fragment for incoming measurements.
		:param str inputSeries: The name of the series for incoming measurements.
		:param float timeIntervalMinutes: The interval for which to calculate consumption values.
		:param str outputFragment: The name of the fragment for generated measurements.
		:param str outputSeries: The name of the series for generated measurements.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'inputFragment':inputFragment,
			'inputSeries':inputSeries,
			'timeInterval':timeIntervalMinutes * 60.0,
			'outputFragment':outputFragment,
			'outputSeries':outputSeries,
		}
		return SmartRule(RULE_CALCULATE_ENERGY, config, self)

	def build_onAlarmExecuteOperation(self, alarmTypes, operation):
		"""
		Build a smart rule object for the rule "On alarm execute operation".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param alarmTypes: The types of alarms that trigger the rule.
		:type alarmTypes: str or list[str]
		:param dict[str,any] operation: The operation that will be sent. It must be a dictionary representing a JSON description of the operation.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'alarmType': self._seq_to_str(alarmTypes),
			'operation': operation,
		}
		return SmartRule(RULE_ON_ALARM_EXECUTE_OPERATION, config, self)

	def build_onMeasurementThresholdCreateAlarm(self, dataPointObjectID=None, alarmType='c8y_ThresholdAlarm', alarmText='Thresholds exceeded'):
		"""
		Build a smart rule object for the rule "On measurement threshold create alarm".

		To deploy it to Cumulocity IoT, call the `~SmartRule.deploy` method.

		:param str dataPointObjectID: The ID of the Data Point Library object to use to find the values for the red and yellow ranges.
		:param str alarmType: The type of raised alarms.
		:param str alarmText: The alarm message.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""
		config = {
			'kpiId': dataPointObjectID,
			'alarmType': alarmType,
			'alarmText':alarmText,
		}
		return SmartRule(RULE_THRESHOLD, config, self)

	@staticmethod
	def _seq_to_str(l):
		if isinstance(l, list):
			return ','.join(l)
		return str(l)

	def _parseSmartRule(self, dictToParse):
		"""
		Create a smart rule object by parsing a response from the server.

		:param dictToParse: Response received from the server.
		:return: A smart rule object.
		:rtype: :class:`SmartRule`
		"""

		ruleType = dictToParse['ruleTemplateName']
		ruleName = dictToParse['name']
		config = dictToParse['config']
		enabled = dictToParse['enabled']
		enabledSources = dictToParse['enabledSources']
		disabledSources = dictToParse['disabledSources']

		rule = SmartRule(ruleType, config, self)\
				.setRuleName(ruleName, addTestPrefix=False)\
				.setEnabled(enabled)\
				.setEnabledSources(enabledSources)\
				.setDisabledSources(disabledSources)

		if 'c8y_Context' in dictToParse:
			managedObject = dictToParse['c8y_Context']['id']
			rule.setLocal(managedObject)
		else:
			rule.setGlobal()

		rule._extractAndSaveIds(dictToParse)
		return rule