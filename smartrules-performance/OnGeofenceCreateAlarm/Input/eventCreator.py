# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import random,time,math
from apamax.eplapplications.perf import ObjectCreator

TARGET_ALARM_RATE = 2 # per second
Inside_GeoFence = [
	{
	'lng':2.0,
	'lat':2.0
	},
	{
	'lng':3,
	'lat':3
	},
	{
	'lng':1.978,
	'lat':3.75
	},
	{
	'lng':2.78,
	'lat':3.335
	}
]
Outside_GeoFence = [
	{
	'lng':0.78,
	'lat':-29.78
	},
	{
	'lng':-1.22,
	'lat':-24.98
	},
	{
	'lng':5.0,
	'lat':5.0
	},
	{
	'lng':6.0,
	'lat':7.94
	}
]
class EventCreator(ObjectCreator):

	def __init__(self, event_input_rate, total_devices, trigger):
		super(EventCreator, self).__init__()
		
		self.event_type = 'position'
		self.eventText = 'Position update'
		self.trigger = trigger
		self.alarm_frequency = (event_input_rate * total_devices) / TARGET_ALARM_RATE
		if self.trigger == 'both':
			# 1 alarm is generated for each toggle. So we need to hold the duration for twice as long to 
			# achieve required alarm rate
			self.alarm_frequency = self.alarm_frequency * 2  

		if self.alarm_frequency < 2:
			self.alarm_frequency = 2
		else:
			self.alarm_frequency = int(self.alarm_frequency)

		print(self.alarm_frequency)

		self.count = {} # number of measurements send for devices

	def createObject(self, device, time):
		count = self.count.get(device, random.randint(0, self.alarm_frequency))
		self.count[device] = count + 1

		if count % self.alarm_frequency < (self.alarm_frequency / 2):
			lng, lat = self.getIndices(Outside_GeoFence)
			print(f'{time}, {device}, Outside')
		else:
			lng, lat = self.getIndices(Inside_GeoFence)
			print(f'{time}, {device}, Inside')

		return {
			"time": time,
			"type": self.event_type,
			"text": self.eventText,
			"source": {
				"id": device
			},
			"c8y_Position": {
				'lng':lng,
				'lat': lat
			}
		}
		
	def getIndices(self,GeofenceList):
		lng = random.choice(GeofenceList)['lng']
		lat = random.choice(GeofenceList)['lat']
		return lng,lat
