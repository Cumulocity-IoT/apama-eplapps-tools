=====================================================
 Using the eplapp.py command line tool
=====================================================
:Description: Document detailing the use of the eplapp.py tool to perform REST requests to Apama EPL Apps in Cumulocity.


Introduction
-------------

The eplapp.py tool in the scripts directory of the SDK allows you to interact with your Apama EPL apps in Cumulocity using the command line. 

The commands available are:

+ ``list`` - Prints details of your existing EPL apps in Cumulocity.
+ ``deploy`` - Uploads a local .mon file to EPL apps in Cumulocity.
+ ``delete`` - Deletes an EPL app from Cumulocity.
+ ``update`` - Updates one or more of the fields of an existing EPL app in Cumulocity.

All of these commands have the following *mandatory* options for connecting to your Cumulocity tenant: 

+ ``-c | --cumulocity_url <url>`` - The base URL of your Cumulocity tenant.
+ ``-u | --username <username>`` - Your Cumulocity username.
+ ``-p | --password <password>`` - Your Cumulocity password.

Each command also has an *optional* ``-h | --help`` option which prints a usage message for that command, for example:

.. code-block:: shell

    eplapp.py <command> --help


Printing a list of your EPL apps 
---------------------------------
To print a list of all of your existing EPL apps in Cumulocity, you can use the ``list`` command as follows:

.. code-block:: shell
    
    eplapp.py list --cumulocity_url <url> --username <username> --password <password>

For each EPL app the name, description, state, and lists of warnings or errors are printed.  

Deploying to Apama EPL Apps in Cumulocity
----------------------------------------------

The ``deploy`` command has an additional *mandatory* option: 

+ ``-f | --file <file>`` - The path to the .mon file you wish to upload to Cumulocity as an EPL app.

Thus, the minimal command for deploying to Apama EPL Apps would look like the following:

.. code-block:: shell

    eplapp.py deploy -c <url> -u <username> -p <password> -f <monFile>

This would upload an active EPL app with no description and the same name as the .mon file specified. 

The ``deploy`` command also has the following *optional* options:
    
+ ``-n | --name <name>`` - The name of the EPL app to be deployed. This option takes 1 argument. By default, this will be the name of the .mon file specified by the ``--file`` option.
+ ``-d | --description <description>`` - A description of the EPL app. This option takes 1 argument.
+ ``-i | --inactive`` - Deploys the EPL app in an 'inactive' state (by default, the state will be 'active').
+ ``-r | --redeploy`` - Overwrites the contents of an existing EPL app of name specified by the ``--name`` option.

Deleting an EPL app
---------------------

The ``delete`` command also has an additional *mandatory* option: 

+ ``-n | --name <name>`` - The name of the the EPL app you wish to delete from your Cumulocity tenant.

For example:

.. code-block:: shell

    eplapp.py delete -c <url> -u <username> -p <password> -n <name>

Updating an existing EPL app
-----------------------------
You can update the contents, name, description, or state of an existing EPL app in Cumulocity using the ``update`` command
which, like the ``delete`` command, has an additional *mandatory* option:

+ ``-n | --name <name>`` - The name of the EPL app you wish to update.

The ``update`` command also has the following *optional* options, of which at least 1 needs to be specified:

+ ``-w | --new_name <name>`` - The new name of the EPL app to be updated. This option takes 1 argument.
+ ``-f | --file <file>`` - The path to a .mon file containing the new contents of the EPL app to be updated. 
+ ``-d | --description <description>`` - The new description of the EPL app to be updated. This option takes 1 argument.
+ ``-a | --state <active/inactive>`` - The state of the EPL app can be set to either 'active' or 'inactive'.

An example of an ``update`` command where we are changing *all* of the EPL app fields would thus look like the following:

.. code-block:: shell

    eplapp.py update -c <url> -u <username> -p <password> -n <old_name> -w <new_name> -f <monFile> -d "new description" -s active 
