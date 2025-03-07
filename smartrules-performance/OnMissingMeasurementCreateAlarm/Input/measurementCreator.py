# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import random
import math
from apamax.eplapplications.perf import ObjectCreator

class MeasurementCreator(ObjectCreator):

	def __init__(self, measurement_type, measurement_input_rate, time_period):
		super(MeasurementCreator, self).__init__()
		self.measurement_type = measurement_type

		# smartrule checks for missing measurements every minute. So to generate alarm we cannot send measurement for 60s
		# or time_period (whichever is higher) plus an additional 60s to make sure that smartrule has processed the devices
		time_period = max(time_period, 60) + 60 + 10  # 10s grace period

		self.toggle_count = time_period * measurement_input_rate  # number of measurements to send/not send before toggling

		self.count = {}  # number of measurements send for devices


	def createObject(self, device, time):
		# Send measurements 2/3rd of the time. Don't send measurement for 1/3rd of the time to raise alarm
		count = self.count.get(device, random.randint(0, 3 * self.toggle_count))
		self.count[device] = count + 1

		cycle_count = math.floor(count/self.toggle_count)
		if cycle_count % 3 != 1:
			# Send a measurement
			return {
				'time': time,
				"type": self.measurement_type,
				"source": {
					"id": device
				},
				'measurement_frag': {
					'measurement_series': {
						"value": random.uniform(0, 100)
					}
				}
			}
		else:
			# Do not send a measurement
			return None
