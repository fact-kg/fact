@echo off
set ROOTS=kg,kg2,..\fact_physics
python.exe pysrc\check.py --roots %ROOTS% --all
