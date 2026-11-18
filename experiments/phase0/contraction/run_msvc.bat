@echo off
rem run_msvc.bat VSVER LABEL COMPILER FLAGS...: build contraction.cpp with cl or clang-cl, count fused instructions, check.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\%~1\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
cd /d "%~dp0"
set "LABEL=%~2"
set "CC=%~3"
shift
shift
shift
set "FLAGS="
:loop
if "%~1"=="" goto done
set "FLAGS=%FLAGS% %1"
shift
goto loop
:done
%CC% /nologo /std:c++20 /EHsc /O2 /arch:AVX2 %FLAGS% /FAs /Facontraction.asm contraction.cpp /Fe:contraction.exe >build.log 2>&1
if errorlevel 1 goto failed
echo == %LABEL%
python count_fma_msvc.py contraction.asm
contraction.exe 20000 | python check.py
exit /b 0
:failed
echo == %LABEL%: COMPILE FAILED
type build.log
exit /b 1
