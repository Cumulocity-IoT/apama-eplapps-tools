# Copyright (c) 2022 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import random
from apamax.eplapplications.perf import ObjectCreator

TARGET_ALARM_RATE = 1.0/60.0 # per second

class MeasurementCreator(ObjectCreator):

	def __init__(self, measurement_type, measurement_fragment, measurement_series, range_min, range_max, measurement_input_rate, total_devices):
		super(MeasurementCreator, self).__init__()
		self.measurement_type = measurement_type
		self.measurement_fragment = measurement_fragment
		self.measurement_series = measurement_series
		self.range_min = range_min
		self.range_max = range_max
		# The number of measurements between each alarm being triggered
		self.measurements_per_alarm = int((measurement_input_rate * total_devices) / TARGET_ALARM_RATE)
		self.measurements_per_alarm = max(self.measurements_per_alarm,TARGET_ALARM_RATE)
		self.count = {} # number of measurements sent for each device

	def createObject(self, device, time):
		count = self.count.get(device, random.randint(0, self.measurements_per_alarm))
		self.count[device] = count + 1

		if count % self.measurements_per_alarm == 0:
			# Generate an alarm
			value = random.uniform(self.range_min, self.range_max)
		else:
			# Do not generate an alarm
			generate_above_max = random.random() < 0.5 # Generate value above max range with 50% probability

			if generate_above_max:
				value = random.uniform(self.range_max + 1, self.range_max + 100)
			else:
				value = random.uniform(self.range_min - 100, self.range_min - 1)

		return {
			'time': time,
			"type": self.measurement_type,
			"source": {
				"id": device
			},
			self.measurement_fragment: {
				self.measurement_series: {
					"value": value
				}
			}
		}
