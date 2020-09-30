@echo off

rem Copyright (c) 2020 Software AG, Darmstadt, Germany and/or its licensors

rem Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
rem file except in compliance with the License. You may obtain a copy of the License at
rem http://www.apache.org/licenses/LICENSE-2.0
rem Unless required by applicable law or agreed to in writing, software distributed under the
rem License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
rem either express or implied.
rem See the License for the specific language governing permissions and limitations under the License.


setlocal

set THIS_SCRIPT=%~$PATH:0
call :getpath %THIS_SCRIPT
if not defined APAMA_HOME (goto APAMA_HOME_UNDEFINED)

set "PATH=%APAMA_HOME%\third_party\python;%PATH%"
python.exe "%THIS_DIR%\eplapp.py" %* 
goto CHECK

:APAMA_HOME_UNDEFINED
WHERE python >NUL 2>&1
if errorlevel 1 (goto PY_UNDEFINED)
python.exe "%THIS_DIR%\eplapp.py" %* 
goto CHECK

:PY_UNDEFINED
echo Please add an appropriate Python 3 version to your path. Please refer to the System requirements section of the documentaion.
goto END

:CHECK
if NOT %errorlevel% == 0 ( 
	EXIT /B %errorlevel%
)
goto END

:END
endlocal
exit /b

:getpath
set THIS_DIR=%~dp0
exit /b
