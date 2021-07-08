# Copyright (c) 2021 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import random
from apamax.eplapplications.perf import ObjectCreator

TARGET_ALARM_RATE = 2 # per second
DESIRED_MEAN = 100
ABNORMAL_MEAN_TARGET = 102

class MeasurementCreator(ObjectCreator):
	"""
	Generate Measurement values for the AlarmOnAbnormalMeanDeviation app.

	Mostly send value close to 100 so that global mean and per device mean remain close to 100.
	Once in a while (based on the rate of alarm generation compared to the input measurements), generate
	a large value that causes the mean of a device to deviate by the target percentage.
	The same device sends a small value next turn to bring the mean back in line with the global mean.

	Since the app allows up to 1% deviation, the value must shift the mean of the device above 101.
	We use 102 as the target.	
	"""
	def __init__(self, measurement_type, measurement_fragment, measurement_series, window_duration, num_device, per_device_rate):
		super(MeasurementCreator, self).__init__()
		self.measurement_type = measurement_type
		self.measurement_fragment = measurement_fragment
		self.measurement_series = measurement_series
		self.window_duration = window_duration
		self.num_device = num_device
		self.per_device_rate = per_device_rate

		self.counts = {} # The number of measurements sent for devices.
		self.last = {}	# The last measurement values sent for devices.
		# The fraction of the input measurements that should generate an alarm.
		self.targetAlarmFraction = TARGET_ALARM_RATE / (self.num_device * self.per_device_rate)
		# The maximum number of measurements per device that are considered for moving average.
		self.per_device_window_size = self.window_duration * self.per_device_rate
	
	def createObject(self, device, time):
		count = self.counts.get(device, 0)
		self.counts[device] = count + 1

		# If the last value sent was greater than the target abnormal mean then we should send a smaller value this 
		# time to get the mean close to the DESIRED_MEAN again.
		if self.last.get(device, 0) > ABNORMAL_MEAN_TARGET:
			value = DESIRED_MEAN - (self.last[device] - DESIRED_MEAN)
		else:
			if random.random() < self.targetAlarmFraction and count > 0:
				# Generate a value that changes the device-mean to be close to the ABNORMAL_MEAN_TARGET.
				#
				# 1) Find out the number of measurements in the window for the device when a new value is added.
				# 2) Assume that each measurement has a value close to the DESIRED_MEAN.
				# 3) Find the new value which causes the mean to be greater than the ABNORMAL_MEAN_TARGET.
				# 
				# window_size = max (self.per_device_window_size - 1, count)
				# new_sum = window_size * DESIRED_MEAN + value
				# new_avg = new_sum / (window_size + 1)
				#
				# new_avg ~= ABNORMAL_MEAN_TARGET
				# (window_size * DESIRED_MEAN + value) / (window_size + 1) ~= ABNORMAL_MEAN_TARGET
				# (window_size * DESIRED_MEAN + value) ~= window_size * ABNORMAL_MEAN_TARGET + ABNORMAL_MEAN_TARGET
				# value ~= ABNORMAL_MEAN_TARGET + window_size * (ABNORMAL_MEAN_TARGET - DESIRED_MEAN)
				
				window_size = count
				# If the window is full then, one item will be removed from the window.
				if window_size >= self.per_device_window_size:
					window_size = self.per_device_window_size - 1

				value = ABNORMAL_MEAN_TARGET + window_size * (ABNORMAL_MEAN_TARGET - DESIRED_MEAN)
			else:
				# Generate a value very close to the DESIRED_MEAN.
				value = DESIRED_MEAN + (random.random() - 0.5) / 10
		self.last[device] = value
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