@echo off
rem vs.bat DIR COMMAND...: run COMMAND in %USERPROFILE%\kairn-phase0\DIR inside the Visual Studio 2026 x64 developer environment.
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
cd /d "%USERPROFILE%\kairn-phase0\%~1"
shift
set "CMD="
:loop
if "%~1"=="" goto run
set "CMD=%CMD% %1"
shift
goto loop
:run
%CMD%
