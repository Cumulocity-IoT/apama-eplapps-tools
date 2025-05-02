=====================================================
Developing EPL Apps Locally
=====================================================
:Description: Guide to writing EPL apps outside of Cumulocity.

Introduction
--------------
EPL apps can be developed outside of the Streaming Analytics web application, using a local install of Apama and a Visual Studio Code install. This guide goes through the steps for using Visual Studio Code.

Setup
-----

1. **Install Visual Studio Code**: Download and install `Visual Studio Code <https://code.visualstudio.com/>`_.
2. **Install Apama Extension**: Install the `Apama extension <https://marketplace.visualstudio.com/items?itemName=ApamaCommunity.apama-extensions>`_ from the Visual Studio Code Marketplace.
3. **Configure Apama**: Ensure you have an installation of Apama configured. This can be done by:
   - Installing the package provided for your operating system, or
   - Following the steps in the marketplace description to configure WSL with Apama.
   - If your installation is not automatically detected, configure the `Apama Home` value within the extension.

Optionally, you can utilize our `Dev Container <https://github.com/Cumulocity-IoT/cumulocity-analytics-vsc-devcontainer/>`, which will automatically provision Apama and clone this repository. See `Microsoft's instructions for Developing inside a Container <https://code.visualstudio.com/docs/devcontainers/containers>` for more information about Dev Containers.

Create a Project
----------------
Open the VS Code Command Palette, and type `Apama: Create Project in New Folder` to create a new Apama project folder. You will need to select the existing parent directory that will hold the folder first, and then the name of the new folder.

Add Bundles to the Project
--------------------------
There are three ways to add bundles to your project:

- Click the `+` symbol next to the Project in the project pane,
- Use the `Apama: Add Bundle` option in the Command Palette,
- Use the `apama_project` command line tool.

Bundle for EPL apps tools development
-----------------------------------------
Add the EPL Apps bundle from `bundle/EPLApps.bnd` to your project.
