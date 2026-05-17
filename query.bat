@echo off
set SCRIPT_DIR=%~dp0
set ROOTS=%SCRIPT_DIR%kg,%SCRIPT_DIR%kg2,%SCRIPT_DIR%..\fact_physics,%SCRIPT_DIR%..\fact_math,%SCRIPT_DIR%..\fact_computer
python.exe %SCRIPT_DIR%pysrc\rule\query.py --roots %ROOTS% %*
