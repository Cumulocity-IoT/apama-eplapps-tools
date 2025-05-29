=====================================================
Developing EPL Apps Locally
=====================================================
:Description: Guide to writing EPL apps outside of Cumulocity.

Introduction
--------------
EPL apps can be developed outside of the Streaming Analytics web application, using Microsoft Visual Studio Code with either a container or local installation of Apama.

Setup
-----

1. **Install Visual Studio Code**: Download and install `Visual Studio Code <https://code.visualstudio.com/>`_.
2. **Install Apama Extension**: Install the `Apama extension <https://marketplace.visualstudio.com/items?itemName=ApamaCommunity.apama-extensions>`_ from the Visual Studio Code Marketplace.
3. Following the steps listed on the extension page to setup WSL (if using Windows) and to install a container engine for running Apama inside a container, or else install Apama locally.

Create a new project
--------------------

The best way to start EPL Apps development is to create a new repository based on the 
[Streaming Analytics Sample Repository Template](https://github.com/Cumulocity-IoT/streaming-analytics-sample-repo-template). 
Go to that page in GitHub, and click the button to "Use this template" and then "Create a new repository".

To open your new repository in VS Code, open the VS Code command palette (`F1`), run `Dev Containers: Clone Repository in Container Volume` 
and then enter the `https://` link to your GitHub repository. This assumes you have a container engine installed. 
If you **already have a Git repository** for your application, just copy across the `.devcontainer` directory from the above template repository. 

Instead of using VS Code you can use a web browser to open the repository in [GitHub Codespaces](https://github.com/features/codespaces) without installing anything at all. 
If you prefer to use a local installation of Apama instead of a container, you need to `git clone` the [EPL Apps Tools](https://github.com/Cumulocity-IoT/apama-eplapps-tools) 
repository, then clone your own repository and open it as a folder in VS Code. 

If you did not use the template repository to create your project, you need to add bundles to make Apama's APIs available to your application. 
You do this by clicking the `+` symbol next to your project in the "Apama Projects" pane of VS Code. 
To configure your project with access to the standard set of Apama APIs that EPL apps can use, add the EPL Apps bundle from `../../apama-eplapps-tools/bundle/EPLApps.bnd` to your project. 

Test
----
The best way to test whether your EPL app is working is to create a simple automated test for it using `PySys <testing-epl.rst>`_. 

If you prefer a more manual approach, you can also run the `correlator` in a terminal window, and then in another terminal, 
inject your project into that correlator by running `engine_deploy --inject <HOST> <PORT> <PROJECTDIR>`. 
