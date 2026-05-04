@echo off
set ROOTS=kg,kg2,..\fact_physics,..\fact_math,..\fact_computer
python.exe pysrc\check.py --roots %ROOTS% --all
