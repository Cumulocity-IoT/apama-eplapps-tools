=====================================================
Apama EPL Apps Tools 
=====================================================
Introduction
-------------

Tooling to work with Apama EPL Apps. This tooling allows 
you to script uploads of your EPL apps and manage them for CI/CD use cases. 
It also provides extensions to the PySys test framework to allow you 
to simply write tests for your EPL apps and to run them automatically.

See <http://www.apamacommunity.com/docs> <https://cumulocity.com/guides/apama> for further docs.

Disclaimer
----------
These tools are provided as-is and without warranty or support. They do not 
constitute part of the Software AG product suite. Users are free to use, fork and modify them, 
subject to the license agreement. While Software AG welcomes contributions, we cannot guarantee 
to include every contribution in the main project.

Licensing
---------
This project is licensed under the Apache 2.0 license - see https://www.apache.org/licenses/LICENSE-2.0

Apama EPL Apps Tools Version
-------------------------
This version of the SDK supports Apama EPL Apps Tools 10.6.6. 

Documentation
-------------

Complete documentation for Apama EPL Apps Tools can be found `here <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc>`_. 

`Using the eplapp.py command line tool <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc/using-eplapp>`_ is the guide which shows you how to use this tool to perform REST requests to Apama EPL Apps in Cumulocity IoT.

You can read up on how to use PySys to test your EPL apps in `Using PySys to test EPL apps <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc//using-pysys>`_.

To find out how to write a test for your EPL apps please look at `Writing tests for EPL apps <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc//testing-epl>`_.

In order to view documentation on classes for PySys helpers for Apama EPL Apps please see: `PySys helpers <https://SoftwareAG.github.io/apama-eplapps-tools/doc/pydoc/autodocgen/apamax.eplapplications.html#module-apamax.eplapplications>`_.

Repository structure
====================

+-------------------------+----------------------------------------------------------+
| apama-eplapps-tools/    | this directory                                           |
+-------------------------+----------------------------------------------------------+
|     readme.rst          | this file                                                |
+-------------------------+----------------------------------------------------------+
|     doc/                | directory containing documentation                       |
+-------------------------+----------------------------------------------------------+
|     scripts/            | directory containing tools for Apama EPL Applications    |
+-------------------------+----------------------------------------------------------+
|     testframework/      | directory containing PySys extensions                    |
+-------------------------+----------------------------------------------------------+
|     samples/            | directory containing example code demonstrating testing  |
+-------------------------+----------------------------------------------------------+




