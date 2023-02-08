#!/usr/bin/env python3
# Copyright (c) 2023 Software AG, Darmstadt, Germany and/or its licensors

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import getopt
import os
import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'testframework'))
from apamax.eplapplications import C8yConnection, AnalyticsBuilder

from apamax.eplapplications.buildVersions import RELEASE_TRAIN_VERSION
TOOL_VERSION_DESCRIPTION = f'Cumulocity IoT Apama EPL Apps command line tool version {RELEASE_TRAIN_VERSION}'

class AnalyticsBuilderCLI:
	"""Class for interacting with Apama AnalyticsBuilder in Cumulocity using a CLI"""

	class Command:

		def __init__(self, name: str, description: str, usages: list, function, arguments=None, successMessage='', mandatoryOptionsMessage='',
				optionalOptionsMessage='', mandatoryOptions=None, optionalOptions=None):
			"""
			:param usages: List of the command line usages.
			:param function: The EPLapp function to be dynamically called when the command is executed.
			:param arguments: Dictionary of (option, argument) to be fed into the function parameter when the command is executed.
			:param mandatoryOptions: A List of the mandatory options that the command requires to execute. Each option within that list should be a 4-item list where: the first element is the short option (e.g. '-u'); the second element is the long option (e.g. '--username'); the third should be the name of the argument it takes (empty string if it takes no argument); and the fourth element the description of what the option does.
			:param optionalOptions: A list of the optional options for the command (see mandatoryOptions param for more details).
			:param successMessage: The message to be printed upon the successful execution of the command.
			"""
			self.name = name
			self.description = description
			self.usages = usages
			self.mandatoryOptionsMessage = mandatoryOptionsMessage
			self.optionalOptionsMessage = optionalOptionsMessage
			self.function = function
			self.arguments = arguments or {}
			self.mandatoryOptions = mandatoryOptions or []
			self.optionalOptions = optionalOptions or []
			self.successMessage = successMessage

		def parseOptList(self, optlist: list):
			"""
			Validates the command-line options supplied for the command, checking that all
			mandatory options are supplied and no unrecognised options have been specified, and
			updates the commands argument dictionary with the arguments supplied.

			:param optlist: List of (option, argument) tuples
			:return: True if '-h' or '--h' option was included, False otherwise.
			"""
			if len(optlist) == 0: return True

			# Check that options supplied are valid for the given command
			mandatoryOptionsShort = mandatoryOptionsLong = optionalOptionsShort = optionalOptionsLong = []
			if len(self.mandatoryOptions) > 0:
				mandatoryOptionsShort = [row[0] for row in self.mandatoryOptions]
				mandatoryOptionsLong = [row[1] for row in self.mandatoryOptions]
			if len(self.optionalOptions) > 0:
				optionalOptionsShort = [row[0] for row in self.optionalOptions]
				optionalOptionsLong = [row[1] for row in self.optionalOptions]

			for option, argument in optlist:
				option = option.lower()
				if option.startswith('--') and (option in mandatoryOptionsLong or option in optionalOptionsLong):
					if argument == '':
						self.arguments[option[2:]] = True
					else:
						self.arguments[option[2:]] = argument
				elif option in mandatoryOptionsShort:
					# We went to use long version of option as a key in our arguments param:
					index = mandatoryOptionsShort.index(option)
					# [2:] removes '--'
					if argument == '':
						self.arguments[mandatoryOptionsLong[index][2:]] = True
					else:
						self.arguments[mandatoryOptionsLong[index][2:]] = argument
				elif option in optionalOptionsShort:
					# We went to use long version of option as a key in our arguments param:
					index = optionalOptionsShort.index(option)
					if argument == '':
						self.arguments[optionalOptionsLong[index][2:]] = True
					else:
						self.arguments[optionalOptionsLong[index][2:]] = argument
				elif option in ('-h', '--help'):
					return True
				elif option in ('-v', '--version'):
					print(f"{TOOL_VERSION_DESCRIPTION}")
				else:
					raise ValueError(f'Could not execute {self.name} command. Option \'{option}\' is not valid for this command.')

			# Check user has supplied all mandatory options:
			cliOptions = [opt[0] for opt in optlist]
			for mandatoryOptionShort, mandatoryOptionLong in zip(mandatoryOptionsShort, mandatoryOptionsLong):
				if mandatoryOptionShort not in cliOptions \
					and mandatoryOptionLong not in cliOptions:
					raise ValueError(f'The {mandatoryOptionLong} option is mandatory for the \'{self.name}\' command.')

			return False

		def execute(self, optlist: list):
			"""
			Method to parse the option list and execute the command.

			If the --help option is specified, it prints the CLI help message.
			If the --version option is specified, it prints the current release train version.

			Else it creates a connection to Cumulocity, popping the 'cumulocity_url', 'username' and 'password' arguments from the Command's arguments param,
			before creating an EPLApps object that executes the EPLApps command using the Command's 'function' param.
			Lastly, a confirmatory message of success is printed.

			:param optlist: List of (option, argument) tuples
			"""
			printHelpRequested = self.parseOptList(optlist)
			if printHelpRequested:
				cli.printUsage(self.name)
			else:
				connection = C8yConnection(self.arguments.pop('cumulocity_url'), self.arguments.pop('username'), self.arguments.pop('password'))
				ab = AnalyticsBuilder(connection)
				returnValue = self.function(ab, **self.arguments)
				if self.successMessage != '':
					print(f'\n{self.successMessage}')

	def __init__(self):

		self.commands = {
			'deploy': AnalyticsBuilderCLI.Command(
				name='deploy', description='Deploys an EPL (.mon) file to Apama EPL Apps in Cumulocity IoT',
				usages=[
					'analyticsbuilder.py deploy <--cumulocity_url URL> <--username USERNAME> <--password PASSWORD> <--file FILE> [option]*',
					'analyticsbuilder.py deploy [--help]',
					'analyticsbuilder.py deploy [--version]'
				],
				mandatoryOptionsMessage='Mandatory options for deploying a file to Apama EPL Apps:',
				mandatoryOptions=[
					['-c', '--cumulocity_url', 'URL', 'the base URL of your Cumulocity IoT tenant'],
					['-u', '--username', 'USERNAME', 'your Cumulocity IoT username'],
					['-p', '--password', 'PASSWORD', 'your Cumulocity IoT password'],
					['-f', '--file', 'FILE', 'the filepath to the .mon file to be deployed as an EPL app']
				],
				optionalOptionsMessage='Optional options for deploying a file to Apama EPL Apps:',
				optionalOptions=[
					['-n', '--name', 'NAME', 'the name of the EPL app to be deployed. By default this is the name of the file specified'],
					['-d', '--description', 'DESCRIPTION', 'description of the EPL app'],
					['-i', '--inactive', '', 'deploy the EPL app in an \'inactive\' state (by default the state will be \'active\').'],
					['-r', '--redeploy', '', 'overwrite the contents of an existing EPL app']
				],
				function=AnalyticsBuilder.deploy,
				arguments={'inactive': False, 'redeploy': False}, 	# Only need to supply default option arguments
				successMessage='EPL app was successfully deployed.'
			),
			'delete': AnalyticsBuilderCLI.Command(
				name='delete', description='Deletes an existing Analytics Builder model in Cumulocity IoT',
				usages=[
					'analyticsbuilder.py delete <--cumulocity_url URL> <--username USERNAME> <--password PASSWORD> <--name NAME>',
					'analyticsbuilder.py delete [--help]',
					'analyticsbuilder.py delete [--version]'
				],
				mandatoryOptionsMessage='Mandatory options for deleting an Analytics Builder model:',
				mandatoryOptions=[
					['-c', '--cumulocity_url', 'URL', 'the base URL of your Cumulocity IoT tenant'],
					['-u', '--username', 'USERNAME', 'your Cumulocity IoT username'],
					['-p', '--password', 'PASSWORD', 'your Cumulocity IoT password'],
					['-n', '--name', 'NAME', 'the name of the Analytics Builder model to be deleted from Cumulocity IoT'],
				],
				function=AnalyticsBuilder.delete,
				successMessage='Analytics Builder model was successfully deleted.'
			),
			'list': AnalyticsBuilderCLI.Command(
				name='list', description='Prints a list of your existing Analytics Builder models in Cumulocity IoT',
				usages=[
					'analyticsbuilder.py list <--cumulocity_url URL> <--username USERNAME> <--password PASSWORD>',
					'analyticsbuilder.py list [--help]',
					'analyticsbuilder.py list [--version]'
				],
				mandatoryOptionsMessage='Mandatory options for printing list of Analytics Builder models in Cumulocity IoT:',
				mandatoryOptions=[
					['-c', '--cumulocity_url', 'URL', 'the base URL of your Cumulocity IoT tenant'],
					['-u', '--username', 'USERNAME', 'your Cumulocity IoT username'],
					['-p', '--password', 'PASSWORD', 'your Cumulocity IoT password']
				],
				function=lambda *a, **kw: self.printModelList(AnalyticsBuilder.getModels(*a, **kw))
			),
			'update': AnalyticsBuilderCLI.Command(
				name='update', description='Updates an existing EPL app in Cumulocity IoT',
				usages=[
					'analyticsbuilder.py update <--cumulocity_url URL> <--username USERNAME> <--password PASSWORD> <--name NAME> <options>+',
					'analyticsbuilder.py update [--help]',
					'analyticsbuilder.py update [--version]'
				],
				mandatoryOptionsMessage='Mandatory options for updating an EPL app in Cumulocity IoT:',
				mandatoryOptions=[
					['-c', '--cumulocity_url', 'URL', 'the base URL of your Cumulocity IoT tenant'],
					['-u', '--username', 'USERNAME', 'your Cumulocity IoT username'],
					['-p', '--password', 'PASSWORD', 'your Cumulocity IoT password'],
					['-n', '--name', 'NAME', 'the name of the EPL app to be updated'],
				],
				optionalOptionsMessage='Optional options for updating an EPL app (at least 1 is required):',
				optionalOptions=[
					['-w', '--new_name', 'NAME', 'the updated name of the EPL app'],
					['-d', '--description', 'DESCRIPTION', 'the updated description of the EPL app'],
					['-s', '--state', 'active/inactive', 'the updated state of the EPL app'],
					['-f', '--file', 'FILE', 'path to the mon file containing the updated contents for the EPL app']
				],
				function=AnalyticsBuilder.update,
				successMessage='EPL app was successfully updated.'
			)
		}

	def main(self, args) -> int:
		"""
		Main method to parse the command line arguments and execute the command, interacting with Apama EPL Apps in C8Y.

		:return: 0 if the command was executed successfully, or a non-zero error code otherwise.
		"""
		try:
			RELEASE_TRAIN_VERSION='10.15.0'
			optlist, commands = self.parseCommandLineArgs(args)
		except Exception as err:
			print(f'error: Could not parse command line options. {err}')
			self.printUsage()
			return 1		# Option not recognised error

		# Check user has supplied correct number of commands:
		if len(commands) != 1:
			if len(commands) > 1:
				print(f'error: {len(commands)} commands specified {commands} when 1 was expected.')
				self.printUsage()
				return 2 	# Command line syntax error
			else:
				opts = [k.strip('-') for (k,v) in optlist]
				if 'version' in opts or 'v' in opts:
					print (f'{TOOL_VERSION_DESCRIPTION}')
				else:
					self.printUsage()
				return 0
		else:
			command = commands[0].lower()
			# Check user has entered valid command:
			if command not in self.commands:
				print(f'error: \'{command}\' is not a recognised command.')
				self.printUsage()
				return 2	# Command error
			try:
				command = self.commands[command]
				command.execute(optlist)
				return 0 	# Command executed successfully
			except ValueError as err:
				print(f'error: {err}')
				self.printUsage(command.name)
				return 1		# Mandatory arguments not supplied or unrecognised option supplied error
			except FileExistsError as err:
				msg = f'error: {err}'
				if command.name == 'deploy':
					msg += ' If you wish to overwrite this EPL app use the --redeploy option. Otherwise specify a unique name using the --name option'
				print(msg)
				return 4 	# File exists error
			except FileNotFoundError as err:
				print(f'error: {err}')
				return 5		# File not found error
			except TypeError as err:
				print(f'error: {err}')
				return 6 	# File type (invalid mon file)
			except OSError as err:
				print(f'error: {err}')
				return 7		# HTTP Request error
			except IOError as err:
				print(f'error: {err}')
				return 8		# File read error
			except Exception as err:
				print(f'error: {err}')
				return 9		# Unknown error

	def parseCommandLineArgs(self, args):
		"""
		Parses command line arguments.

		:param args: List of arguments supplied on command line.
		:return: a list of (option, argument) tuples; and a list of commands
		"""
		# Get valid short/long options from self.commands for getopt.gnu_getopt method:
		shortopts = 'hv'
		longopts = ['help','version']
		for command in self.commands.values():
			for opt in command.mandatoryOptions + command.optionalOptions:
				needsArgument = (opt[2] != '' and not opt[2].isspace())
				shortopt = opt[0][1:]
				if shortopt not in shortopts:
					shortopts += shortopt + (':' if needsArgument else '')
				longopt = opt[1][2:] + ('=' if needsArgument else '')
				if longopt not in longopts:
					longopts.append(longopt)
		# Parsing command line arguments:
		return getopt.gnu_getopt(args, shortopts, longopts)

	@staticmethod
	def printFormattedTable(table: list, rowFormat: str, *columns: int, **kwargs):
		"""
		Prints a formatted table.

		:param table: An Iterable object representing the table to be printed
		:param rowFormat: A format string for each row of the table
		:param columns: The indexes of the columns to be inserted into the format string for each row
		:param kwargs: Any additional kwargs to be inserted into the format string
		"""
		for row in table:
			print(rowFormat.format(*[row[col] for col in columns], **kwargs))

	@staticmethod
	def calculateColumnWidth(table: list, columnIndex: int, include=1) -> int:
		"""
		Calculates the required width of a column by finding the length of the longest entry in that column

		:param table: The table to be printed
		:param columnIndex: The column index to calculate the width for
		:param include: The number of columns to include in the calculation. If this is greater than one, multiple columns
		will be grouped together in the calculation
		:return: The formatted width of the column(s)
		"""
		return max([sum([len(row[col]) for col in range(columnIndex, columnIndex + include)]) for row in table])

	def printUsage(self, command=None):
		"""
		Prints EPL Apps CLI tool usage information.

		:param command: The command to print the usage information for.
		"""
		print(f'{TOOL_VERSION_DESCRIPTION}.\n')
		if command in self.commands:
			command = self.commands[command]
			print(f'\n{command.description}\n')
			usagesTable = list(zip(*[[('Usages:' if i == 0 else '') for i in range(len(command.usages))], command.usages]))
			self.printFormattedTable(usagesTable, '{:{width}}  {}', 0, 1, width=len(usagesTable[0][0]))
			if len(command.mandatoryOptions) > 0:
				print(f'\n{command.mandatoryOptionsMessage}')
				self.printFormattedTable(
					command.mandatoryOptions,
					'	{:{widths[0]}} | {:{widths[1]}} {:{widths[2]}}	{:{widths[3]}}', 0, 1, 2, 3,
					widths=[self.calculateColumnWidth(command.mandatoryOptions, col) for col in range(4)],
				)
			if len(command.optionalOptions) > 0:
				print(f'\n{command.optionalOptionsMessage}')
				self.printFormattedTable(
					command.optionalOptions,
					'	{:{widths[0]}} | {:{widths[1]}} {:{widths[2]}}	{:{widths[3]}}', 0, 1, 2, 3,
					widths=[self.calculateColumnWidth(command.optionalOptions, col) for col in range(4)]
				)
		else:
			if command is not None: print(f'error: \'{command}\' is not a recognised command')

			usageTable = [
				['Usage:', 'analyticsbuilder.py <command> <options>'],
				['', 'analyticsbuilder.py [--help]', 'analyticsbuilder.py [--version]']
			]
			
			self.printFormattedTable(usageTable, '{:{width}}  {}', 0, 1, width=len(usageTable[0][0]))
			print('\nCommands:')
			self.printFormattedTable(
				[[command.name, command.description] for command in self.commands.values()],
				'	{:{width}}  {}', 0, 1,
				width=len('delete') + 2)

		print('\nOther optional options:')
		print('	-h | --help	print this message')
		print('	-v | --version	print the current version of EPL Apps Tools')


	def printModelList(self, modelJSON: list):
		"""
		Prints a formatted list of Analytics Builder models.

		:param modelJSON: A list of EPL apps in JSON form
		"""
		modelString = '\nAnalytics Builder models:'
		if modelJSON is None or len(modelJSON) == 0:
			modelString += '\nNo EPL apps to display.'
		else:
			for model in modelJSON:
				modelString += '\n'
				printMessage = [
					['name', model['name']],
					['description', model['description']],
					['state', model['state']],
					['mode', model['mode']],
					['errors', model['runtimeError']]
				]
				for row in printMessage:
					modelString += '\n{:>{padd}}:	{}'.format(*[row[col] for col in (0, 1)], padd=len('description')+1)
		print(modelString)

if __name__ == "__main__":
	cli = AnalyticsBuilderCLI()
	sys.exit(cli.main(sys.argv[1:]))


