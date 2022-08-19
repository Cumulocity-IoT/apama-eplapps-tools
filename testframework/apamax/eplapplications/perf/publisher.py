#!/usr/bin/env python3

## License
# Copyright (c) 2021-2022 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import argparse
import random
import time
import math
import json
import sys, os
import importlib.util
import urllib.error
from datetime import datetime
from apamax.eplapplications.connection import C8yConnection
from apamax.eplapplications.perf import ObjectCreator

# Maximum batch size
MAX_BATCH_SIZE = 2000

class DefaultObjectCreator:
	def createObject(self, device, time):
		return {
			'time': time,
			"type": 'my_measurement',
			"source": {
				"id": device
			},
			'my_fragment': {
				'my_series': {
					"value": random.uniform(0, 100)
				}
			}
		}

# '/measurement/measurements', '/event/events', '/alarm/alarms'
MEASUREMENT_TYPE_NAME = 'measurements'
MEASUREMENT_RESOURCE_URL = '/measurement/measurements'
MEASUREMENT_CONTENT_TYPE = 'application/vnd.com.nsn.cumulocity.measurementcollection+json'

EVENT_TYPE_NAME = 'event'
EVENT_RESOURCE_URL = '/event/events'
EVENT_CONTENT_TYPE = 'application/vnd.com.nsn.cumulocity.event+json'

ALARM_TYPE_NAME = 'alarm'
ALARM_RESOURCE_URL = '/alarm/alarms'
ALARM_CONTENT_TYPE = 'application/vnd.com.nsn.cumulocity.alarm+json'

class DataPublisher(object):
	def __init__(self, base_url, username, password, devices, per_device_rate, duration, resource_url, processing_mode='CEP', object_creator_info=None):
		self.connection = C8yConnection(base_url, username, password)
		self.devices = devices
		self.per_device_rate = per_device_rate
		self.duration = duration
		self.resource_url = resource_url
		self.processing_mode = processing_mode
		self.supportsBatchSend = False
		self.content_type = None
		self.type_name = None

		if self.resource_url == MEASUREMENT_RESOURCE_URL:
			self.type_name = MEASUREMENT_TYPE_NAME
			self.content_type = MEASUREMENT_CONTENT_TYPE
			self.supportsBatchSend = True	# Only measurents support batched sending
		elif self.resource_url == EVENT_RESOURCE_URL:
			self.type_name = EVENT_TYPE_NAME
			self.content_type = EVENT_CONTENT_TYPE
		elif self.resource_url == ALARM_RESOURCE_URL:
			self.type_name = ALARM_TYPE_NAME
			self.content_type = ALARM_CONTENT_TYPE
		else:
			raise Exception(f'Unsupported resource type: {self.resource_url}')

		if object_creator_info:
			self.object_creator = self.load_object_creator(object_creator_info)
		else:
			self.object_creator = DefaultObjectCreator()

	def load_object_creator(self, object_creator_info):
		"""
		Load object creator class from the specified Python file and create
		and instance of it using the specified parameters.
		"""
		try:
			object_creator_info = json.loads(object_creator_info)
			module_file = object_creator_info.get('file', '')
			if module_file == '':
				raise Exception(f'Invaid value for the python file containing object creator: {module_file}')
			if not module_file.endswith('.py'):
				raise Exception(f'Expected python file for the object creator: {module_file}')
			creator_class_name = object_creator_info.get('className')
			if creator_class_name == '':
				raise Exception(f'Invaid value for the object creator class: {creator_class_name}')
			constructor_params = object_creator_info.get('constructorParams', [])
			module_name = os.path.basename(module_file)[:-3]
			spec = importlib.util.spec_from_file_location(module_name, module_file)
			if spec is None:
				raise Exception(f'Unable to import module: {module_file}')
			the_module = importlib.util.module_from_spec(spec)
			if the_module is None:
				raise Exception(f'Unable to import module: {module_file}')
			spec.loader.exec_module(the_module)
			the_class = getattr(the_module, creator_class_name, None)
			if the_class is None:
				raise Exception(f'Class {object_creator_info} not found in  module: {module_file}')
			if not issubclass(the_class, ObjectCreator):
				raise Exception(f'Class {creator_class_name} is not a subclass of {ObjectCreator.__name__}')
			# Create object
			try:
				the_object = the_class(*constructor_params)
			except Exception as ex:
				raise Exception(f'Unable to create new instance of {creator_class_name}: {ex}').with_traceback(ex.__traceback__) 
			
			if not isinstance(the_object, ObjectCreator):
				raise Exception(f'Class {creator_class_name} is not a subclass of {ObjectCreator.__name__}')
			return the_object
		except Exception as ex:
			raise Exception(f'Failed to create object creator instance: {ex}').with_traceback(ex.__traceback__)

	def getUTCTime(self):
		""" 
			Gets a Cumulocity IoT-compliant UTC timestamp string for the current time.

			:return: Timestamp string.
			:rtype: str
		"""
		t = datetime.utcnow()
		if t.microsecond == 0:
			return t.isoformat() + '.000Z'
		else:
			return t.isoformat()[:-3] + 'Z'

	def do_send(self, body):
		"""Send event(s) to Cumulocity IOT."""
		headers = {
					'Content-Type': self.content_type,
					'X-Cumulocity-Processing-Mode': self.processing_mode
				}
		startTime = time.time()
		MAX_RETRY_TIME = 60.0
		while time.time() < startTime + MAX_RETRY_TIME:
			try:
				self.connection.request(
					'POST',
					self.resource_url,
					body=json.dumps(body),
					headers=headers
				)
				return
			except urllib.error.HTTPError as ex:
				# Retry in case of 5XX error.
				if ex.code // 100 == 5:
					print(f'WARN: Failed to send to Cumulocity IoT, retrying; error={ex}')
					time.sleep(0.5)
				else:
					print(f'ERROR: Failed to send to Cumulocity IoT; error={ex}')
					raise ex
		
		print(f'ERROR: Failed to send to Cumulocity IoT after trying for {MAX_RETRY_TIME} seconds; headers={headers}, body={body}')

	def run(self):
		print(f'Started publishing Cumulocity {self.type_name} with rate of {self.per_device_rate} objects per device per second, with processing mode {self.processing_mode} to devices: {self.devices}')
		sys.stdout.flush()
		# Find total number of events to send per seconds
		per_sec_total = float(len(self.devices) * self.per_device_rate)
		# Interval between each event - we sleep for this amount of time
		send_interval = 1.0 / per_sec_total
		
		# The index of next device to send event for (we send events in round robin fashion for each device).
		device_index = 0
		start_time = time.time() - send_interval
		finish_time = (time.time() + self.duration) if self.duration is not None else float('inf')
		logged_time = 0	# last time a message was logged about number of events sent
		total_sent = 0	# total number of events sent
		total_batch = 0 # total number of batches sent
		while time.time() < finish_time:
			now_time = time.time()
			# Find number of events to send; usually it should be 1 but sometime thread might
			# sleep for longer period. So batch together all the events which should have been sent by now.
			num_to_send = math.ceil(per_sec_total * (now_time-start_time)) - total_sent
			num_to_send = min(num_to_send, MAX_BATCH_SIZE)	# have some upper bound on batch size
			if num_to_send > 0:
				batch = []
				for _ in range(num_to_send):
					if device_index >= len(self.devices):
						device_index = 0 # wrap around
					
					obj = self.object_creator.createObject(self.devices[device_index],self.getUTCTime())
					if obj:
						batch.append(obj)
					
					device_index += 1

				if self.supportsBatchSend:
					if len(batch) > 0:
						self.do_send({self.type_name: batch})
				else:
					for e in batch:
						self.do_send(e)

				total_sent += len(batch)
				total_batch += 1

				# log total events sent every five seconds
				if time.time() - logged_time > 5.0:
					print(f'{time.time()}: sent total {total_sent} events with rate {total_sent/(now_time-start_time)} eps and average batch size of {total_sent/total_batch} events')
					sys.stdout.flush()
					logged_time = time.time()

			# sleep if we have some time remaining before the next batch
			sleep_duration = now_time + send_interval - time.time()
			if sleep_duration > 0:
				time.sleep(sleep_duration)
			

def main():
	parser = argparse.ArgumentParser(description='Cumulocity Data Publishing Process', add_help=True)
	parser.add_argument('--base_url', type=str, help='Tenant URL')
	parser.add_argument('--username', type=str, help='Username of tenant user')
	parser.add_argument('--password', type=str, help='Password of tenant user')
	parser.add_argument('--devices', type=str, help='List of devices in JSON string')
	parser.add_argument('--per_device_rate', type=float, help='Per device data rate')
	parser.add_argument('--duration', type=float, required=False, help='Total duration')
	parser.add_argument('--resource_url', type=str, default='/measurement/measurements', help='The url for the resource to publish.')
	parser.add_argument('--processing_mode', type=str, default='CEP', help='The cumulocity processing mode. Possible values are CEP, PERSISTENT, TRANSIENT and QUIESCENT')
	parser.add_argument('--object_creator_info', type=str, required=False, help='Info about the object creator in JSON string')
	args = parser.parse_args()

	if args.resource_url not in ['/measurement/measurements', '/event/events', '/alarm/alarms']:
		raise Exception(f'Unsupported object type: {args.resource_url}')

	publisher = DataPublisher(base_url=args.base_url, username=args.username, password=args.password,
					devices=json.loads(args.devices), per_device_rate=args.per_device_rate, duration=args.duration,
					resource_url=args.resource_url, processing_mode=args.processing_mode, object_creator_info=args.object_creator_info)
	publisher.run()

if __name__ == '__main__':
	try:
		main()
	except Exception as ex:
		print(f'ERROR: DataPublisher failed: {ex}')
		import traceback 
		traceback.print_exc()
		sys.stdout.flush()
