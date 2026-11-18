@echo off
rem The contraction matrix on Windows x64 (MSVC from Visual Studio 2026 Build Tools).
call "%~dp0run_msvc.bat" 18 "msvc-19.5x x64 /O2 /arch:AVX2 [default: /fp:precise]" cl
call "%~dp0run_msvc.bat" 18 "msvc-19.5x x64 /O2 /arch:AVX2 /fp:contract" cl /fp:contract
call "%~dp0run_msvc.bat" 18 "msvc-19.5x x64 /O2 /arch:AVX2 /fp:strict" cl /fp:strict
call "%~dp0run_msvc.bat" 18 "msvc-19.5x x64 /O2 /arch:AVX2 /fp:except-" cl /fp:precise /fp:except-
call "%~dp0run_msvc.bat" 18 "msvc-19.5x x64 /Od /arch:AVX2" cl /Od
