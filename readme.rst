=====================================================
Apama EPL Apps Tools 
=====================================================
Introduction
-------------

Tooling to work with Apama EPL Apps. This tooling allows 
you to script uploads of your EPL apps and manage them for CI/CD use cases. 
It also provides extensions to the PySys test framework to allow you 
to simply write tests for your EPL apps and to run them automatically.

Disclaimer
----------
These tools are provided as-is and without warranty or support. They do not 
constitute part of the Cumulocity GmbH product suite. Users are free to use, fork and modify them, 
subject to the license agreement. While Cumulocity GmbH welcomes contributions, we cannot guarantee 
to include every contribution in the main project.

Licensing
---------
Copyright 2019-present Cumulocity GmbH
This project is licensed under the Apache 2.0 license - see https://www.apache.org/licenses/LICENSE-2.0

Apama EPL Apps Tools Version
-------------------------
Use the 'main' branch for the current release or switch to the appropriate branch for Long-term support (LTS) / Maintenance releases.

Documentation
-------------

Complete documentation for Apama EPL Apps Tools can be found `here <https://cumulocity-iot.github.io/apama-eplapps-tools>`_.

`Using the eplapp.py command line tool <https://cumulocity-iot.github.io/apama-eplapps-tools/using-eplapp>`_ is the guide which shows you how to use this tool to perform REST requests to Apama EPL Apps in Cumulocity.

You can read up on how to use PySys to test your EPL apps in `Using PySys to test EPL apps <https://cumulocity-iot.github.io/apama-eplapps-tools/using-pysys>`_.

To find out how to write a test for your EPL apps look at `Writing tests for EPL apps <https://cumulocity-iot.github.io/apama-eplapps-tools/testing-epl>`_.

To find out how to performance test your EPL apps look at `Performance testing EPL apps <https://cumulocity-iot.github.io/apama-eplapps-tools/performance-testing>`_.

In order to view the documentation on classes for PySys helpers for Apama EPL Apps see: `PySys helpers <https://cumulocity-iot.github.io/apama-eplapps-tools/autodocgen/apamax.eplapplications.html#module-apamax.eplapplications>`_.

To configure a local development environment see: `Developing EPL apps locally <https://cumulocity-iot.github.io/apama-eplapps-tools/developing-epl-apps-locally>`_.

See `Apama Documentation <https://cumulocity.com/apama/docs/latest>`_, `Streaming Analytics guide <https://cumulocity.com/docs/streaming-analytics>`_ and `PySys Documentation <https://pysys-test.github.io/pysys-test>`_ for further docs.

System requirements
-------------------
This SDK requires an installation of Python 3.7+ and will run on either Windows or Linux.

The EPL apps test framework requires you to have an installation of PySys. See `PySys Documentation <https://pysys-test.github.io/pysys-test>`_ for details. If you want the option of running tests locally, you will also need an installation of the latest Apama, which can be obtained from `Apama Downloads <https://download.cumulocity.com/Apama>`_. If you choose to install Apama, you may skip the manual installation of Python and PySys as both are shipped with Apama.


Repository structure
====================

+-------------------------+----------------------------------------------------------------------+
| apama-eplapps-tools/    | this directory                                                       |
+-------------------------+----------------------------------------------------------------------+
|    readme.rst           | this file                                                            |
+-------------------------+----------------------------------------------------------------------+
|    doc/                 | directory containing documentation                                   |
+-------------------------+----------------------------------------------------------------------+
|    scripts/             | directory containing tools for Apama EPL Applications                |
+-------------------------+----------------------------------------------------------------------+
|    testframework/       | directory containing PySys extensions                                |
+-------------------------+----------------------------------------------------------------------+
|    samples/             | directory containing example code demonstrating testing              |
+-------------------------+----------------------------------------------------------------------+
|    samples-performance/ | directory containing example code demonstrating performance testing  |
+-------------------------+----------------------------------------------------------------------+

Change Log
-----------

See `Change Log <changelog.rst>`_ for changes.
