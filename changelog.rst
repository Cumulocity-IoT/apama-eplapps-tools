============
Change Log
===========

26.95.0
---------
+ The EPL Apps Tools is no longer supported natively on Windows environments. For Windows users, we recommend switching to a WSL-based (Windows Subsystem for Linux) environment using Debian. You may wish to use the [Apama Extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ApamaCommunity.apama-extensions) for developing EPL apps. 

25.283.0
---------
+ By default, the EPL Apps Tools test framework clears all alarms on the tenant during startup. This behavior can now be disabled by setting the `clearAllActiveAlarmsDuringTenantPreparation` property to `false` in the PySys project configuration.

25.219.0
---------
+ The EPL Apps Tools test framework supports Notifications 2.0 for receiving notifications from Cumulocity.

24.0.0
-------
+ The EPL Apps tools test framework now moves to a continuous delivery (CD) model.

10.15.0.4
----------
+ An issue where the rendered documentation pages were showing a 404 error when accessed has been resolved.

10.14.0.0
----------

+ Added support for testing the performance of smart rules. Check the documentation for more details.

10.11.0.0
----------

+ Added support for testing the performance of EPL apps. Check the documentation for more details.
