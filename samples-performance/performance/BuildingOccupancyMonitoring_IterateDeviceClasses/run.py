# Copyright (c) 2021-present Cumulocity GmbH, Duesseldorf, Germany and/or its affiliates and/or their licensors.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

from pysys.constants import *
from apamax.eplapplications.perf.basetest import EPLAppsPerfTest
import os

class PySysTest(EPLAppsPerfTest):
	"""
		Configuration defined below can be changed when running the test using -XconfigName=configValue.
		For example:
		```
		pysys run -XnumOfBuildings=10 -XbuildingMeasurementFragment="building_frag" TestName
		```
	"""
	
	##### Test configurations ###
	# Restart the Apama microservice while preparing the tenant for running the performance test.
	restartMicroservice = True

	# The duration (in seconds) for the app to run for measuring the performance for each variation.
	testDuration = 300.0

	# The processing mode to use when publishing simulated measurements to Cumulocity IoT.
	cumulocityProcessingMode = 'CEP'

	##### App configuration #####
	# The type of ManagedObjects representing a building.
	buildingType = 'type_building'
	# The type of ManagedObjects representing an access point.
	accessPointType = 'type_access_point'
	# The type of measurements containing the count of people entered and exited a building via an access point.
	accessPointMeasurementType = 'building_entry_exit'
	# The measurement fragments containing the count of people who entered and exited a building via an access point.
	accessPointMeasurementFragment = 'access_point_crossed'
	# The measurement series containing the count of people who entered a building via an access point.
	accessPointEnteredSeries = 'people_entered'
	# The measurement series containing the count of people who exited a building via an access point.
	accessPointExitedSeries = 'people_exited'

	# The type of measurement generated by buildings with total occupancy count of the building.
	buildingMeasurementType = 'building_population'
	# The fragment of measurements generated by buildings.
	buildingMeasurementFragment = 'number_of_people'
	# The series of measurements generated by buildings.
	buildingMeasurementSeries = 'count'

	# The occupancy threshold for buildings. An alarm is raised if the occupancy of a building is more than this value.
	occupancyThreshold = 1000
	# The type of the raised alarm.
	alarmType = 'ThresholdExceededAlarm'
	# The severity of the raised alarm.
	alarmSeverity = 'MAJOR'

	# The fragment type for created operations.
	operationFragment = 'buildingOccupancyAlarmNotCleared'
	# The duration (in minutes) to wait for an Alarm to be cleared before creating an Operation.
	alarmClearDurationMin = 0.5

	##### Configuration for simulators. #####

	# List of the combinations to test.
	combinations = [
		# (<DeviceClass>, <PerDeviceRate>, [(<NumBuilding>, <AccessPointPerBuilding>), ...])
		('D', 0.1, [(2, 5), (10, 5), (10, 10), (50, 10), (100, 10)]),
		('E', 1, [(2, 5), (10, 5), (10, 10), (50, 10), (100, 10)]),
		('F', 1000, [(1, 1), (2, 1), (5, 2)]),
	]

	def execute(self):
		totalBuildings = 0
		for n, (deviceClass, inputRate, deviceConfig) in enumerate(self.combinations):
			for (numOfBuildings, numOfAccessPointsPerBuilding) in deviceConfig:
				description = f'{numOfBuildings} buildings with {numOfAccessPointsPerBuilding} class {deviceClass} access-points each (max {inputRate} eps/device)'

				self.log.info(f'Testing {description}')
				
				# Prepare the tenant for the test run.
				self.prepareTenant(restartMicroservice=self.restartMicroservice)

				# Start performance monitoring.
				perfMonitor = self.startPerformanceMonitoring()

				# Save the start time for querying generated alarms and operations.
				self.startTime = self.getUTCTime()

				# Create devices for buildings and their access points before EPL Apps are 
				# deployed as they look up devices at the start.
				buildings = {}
				for i in range(numOfBuildings):
					accessPoints = [self.createTestDevice(f'accesspoint_{i}_{j}', type=self.accessPointType) for j in range(numOfAccessPointsPerBuilding)]
					building = self.createTestDevice(f'building_{i}', type=self.buildingType, children=accessPoints)
					buildings[building] = accessPoints

				totalBuildings = totalBuildings + numOfBuildings
				# Deploy the sample app.
				self.deploySampleApp(totalBuildings)

				# Start simulators.
				self.startSimulators(buildings, inputRate, numOfAccessPointsPerBuilding)

				# Wait for enough performance data to be gathered.
				self.wait(self.testDuration)

				# Stop performance monitoring.
				perfMonitor.stop()
				
				# Save the end time.
				self.endTime = self.getUTCTime()

				# Generate the HTML report.
				self.generateHTMLReport(description,
					testConfigurationDetails=self.getTestConfigurationDetails(numOfBuildings, numOfAccessPointsPerBuilding, inputRate),
					extraPerformanceMetrics=self.getExtraPerformanceMetrics())

	def deploySampleApp(self, totalBuildings):
		"""Deploy the sample app."""
		# Configure the app by replacing the placeholder values with the actual configured values
		appConfiguration = {
			## BuildingAccessPointMonitoring config ##
			'BUILDING_MO_TYPE': self.buildingType,
			'ACCESS_POINT_MO_TYPE': self.accessPointType,

			'ACCESS_POINT_MEASUREMENT_TYPE': self.accessPointMeasurementType,
			'ACCESS_POINT_MEASUREMENT_FRAGMENT': self.accessPointMeasurementFragment,
			'ACCESS_POINT_ENTERED_SERIES': self.accessPointEnteredSeries,
			'ACCESS_POINT_EXITED_SERIES': self.accessPointExitedSeries,

			'BUILDING_MEASUREMENT_TYPE': self.buildingMeasurementType,
			'BUILDING_MEASUREMENT_FRAGMENT': self.buildingMeasurementFragment,
			'BUILDING_MEASUREMENT_SERIES': self.buildingMeasurementSeries,

			## AlarmOnThreshold config ##
			'MEASUREMENT_TYPE': self.buildingMeasurementType,
			'MEASUREMENT_FRAGMENT': self.buildingMeasurementFragment,
			'MEASUREMENT_SERIES': self.buildingMeasurementSeries,
			'MEASUREMENT_THRESHOLD': self.occupancyThreshold,

			'ALARM_TYPE': self.alarmType,
			'ALARM_SEVERITY': self.alarmSeverity,

			## OperationOnAlarmNotCleared config ##
			'ALARM_CLEAR_DURATION_MINUTES': self.alarmClearDurationMin,
			'OPERATION_FRAGMENT': self.operationFragment,
		}

		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'AlarmOnMeasurementThreshold.mon'),
			os.path.join(self.output, 'AlarmOnMeasurementThreshold.mon'), replacementDict=appConfiguration, marker='@')
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'BuildingOccupancyCalculation.mon'),
			os.path.join(self.output, 'BuildingOccupancyCalculation.mon'), replacementDict=appConfiguration, marker='@')
		self.copyWithReplace(os.path.join(self.project.EPL_APPS, 'OperationOnAlarmNotCleared.mon'),
			os.path.join(self.output, 'OperationOnAlarmNotCleared.mon'), replacementDict=appConfiguration, marker='@')
		
		# deploy applications
		self.eplapps.deploy(os.path.join(self.output, "OperationOnAlarmNotCleared.mon"), name='PYSYS_OperationOnAlarmNotCleared',
					   redeploy=True, description='Application under test, injected by test framework')
		self.eplapps.deploy(os.path.join(self.output, "AlarmOnMeasurementThreshold.mon"), name='PYSYS_AlarmOnMeasurementThreshold',
					   redeploy=True, description='Application under test, injected by test framework')
		self.eplapps.deploy(os.path.join(self.output, "BuildingOccupancyCalculation.mon"), name='PYSYS_BuildingAccessPointsMonitoring',
					   redeploy=True, description='Application under test, injected by test framework')

		self.waitForGrep(self.platform.getApamaLogFile(), expr="Building occupancy calculation setup completed", condition=f"=={totalBuildings}")


	def startSimulators(self, buildings, inputRate, numOfAccessPointsPerBuilding):
		"""Start Measurement simulators for the sample app."""
		numOfBuildings = len(buildings)

		# Use separate simulator for each building.
		for building, accessPoints in buildings.items():
			self.startMeasurementSimulator(accessPoints, inputRate,
					f'{self.input}/measurementCreator.py', 'MeasurementCreator', [
						self.accessPointMeasurementType,
						self.accessPointMeasurementFragment, 
						self.accessPointEnteredSeries, 
						self.accessPointExitedSeries, 
						numOfBuildings,
						numOfAccessPointsPerBuilding,
						inputRate,
						self.occupancyThreshold,
						self.alarmClearDurationMin,
					], duration=self.testDuration, processingMode=self.cumulocityProcessingMode)

			# Stagger the publishers so that we don't produce alarms at the same time.
			self.wait(1/numOfBuildings)

	def getAlarmsCount(self):
		""" Get count of alarms raised and alarms cleared during test run. """
		alarms = self.getAlarms(type=self.alarmType, dateFrom=self.startTime, dateTo=self.endTime)
		raised = len(alarms)
		cleared = 0
		for alarm in alarms:
			if alarm.get('status', '') == 'CLEARED':
				cleared += 1
		return (raised, cleared)

	def getOperationsCount(self):
		""" Get count of operations created during test run. """
		return len(self.getOperations(fragmentType=self.operationFragment, dateFrom=self.startTime, dateTo=self.endTime))

	def getExtraPerformanceMetrics(self):
		""" Get details on alarms and operations. """
		(raised, cleared) = self.getAlarmsCount()
		operations = self.getOperationsCount()
		return {
			'Alarms Raised': raised,
			'Alarms Cleared': cleared,
			'Operations created': operations
		}

	def getTestConfigurationDetails(self, numOfBuildings, numOfAccessPointsPerBuilding, inputRatePerAccessPoint):
		"""Get description of the test configurations to include in the report."""
		return {
			'Test duration (secs)': self.testDuration,
			'Restart Apama MicroService': self.restartMicroservice,
			'Cumulocity Processing Mode': self.cumulocityProcessingMode,
			
			'Number of buildings': numOfBuildings,
			'Number of access points per building': numOfAccessPointsPerBuilding,
			'Input rate per access point': inputRatePerAccessPoint,

			'Building type': self.buildingType,
			'Access point type': self.accessPointType,

			'Access point measurement type': self.accessPointMeasurementType,
			'Access point measurement fragment': self.accessPointMeasurementFragment,
			'Access point entry series': self.accessPointEnteredSeries,
			'Access point exit series': self.accessPointExitedSeries,

			'Building measurement type': self.buildingMeasurementType,
			'Building measurement fragment': self.buildingMeasurementFragment,
			'Building measurement series': self.buildingMeasurementSeries,
			'Building occupancy threshold': self.occupancyThreshold,

			'Alarm clear duration (minutes)': self.alarmClearDurationMin,

			'Alarm type': self.alarmType,
			'Alarm severity': self.alarmSeverity,
		}
