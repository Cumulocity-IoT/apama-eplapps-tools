# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import random
from apamax.eplapplications.perf import ObjectCreator

class MeasurementCreator(ObjectCreator):
	def __init__(self, measurement_type, measurement_fragment, measurement_series, upperBound=100):
		super(MeasurementCreator, self).__init__()
		self.measurement_type = measurement_type
		self.measurement_fragment = measurement_fragment
		self.measurement_series = measurement_series
		self.upperBound = float(upperBound)
	
	def createObject(self, device, time):
		value = random.uniform(0, self.upperBound)
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