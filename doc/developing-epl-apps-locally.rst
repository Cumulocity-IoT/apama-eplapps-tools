=====================================================
Developing EPL Apps Locally
=====================================================
:Description: Guide to writing EPL apps outside of Cumulocity.

Introduction
--------------
EPL apps can be developed outside of the Streaming Analytics web application, using a local installation of Apama and Visual Studio Code. 

Setup
-----

1. **Install Visual Studio Code**: Download and install `Visual Studio Code <https://code.visualstudio.com/>`_.
2. **Install Apama Extension**: Install the `Apama extension <https://marketplace.visualstudio.com/items?itemName=ApamaCommunity.apama-extensions>`_ from the Visual Studio Code Marketplace.
3. Following the steps listed on the extension page to either install Apama locally, or to use an Apama container.

Optionally, you can use our `Dev Container <https://github.com/Cumulocity-IoT/cumulocity-analytics-vsc-devcontainer/>`_, which will automatically provision Apama and clone this repository. See Microsoft's instructions for `Developing inside a Container <https://code.visualstudio.com/docs/devcontainers/containers>`_.

Create a new project
--------------------
Open the VS Code Command Palette, and type `Apama: Create Project in New Folder` to create a new Apama project folder. You will need to select the existing parent directory that will hold the folder first, and then the name of the new folder.

To configure your project with access to the Apama APIs that EPL apps can use, add the EPL Apps bundle from `bundle/EPLApps.bnd` to your project. 

To add a bundle to your project, either click the `+` symbol next to your project in the "Apama Projects" pane, or type `Apama: Add Bundle` into the Command Palette. 

Test
----
The best way to test whether your EPL app is working is to create a simple automated test for it using `PySys <testing-epl.rst>`_. 

If you prefer a more manual approach, you can also run the `correlator` in a terminal window, and then in another terminal, 
inject your project into that correlator by running `engine_deploy --inject <HOST> <PORT> <PROJECTDIR>`. 
