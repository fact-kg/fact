@echo off
set ROOTS=kg,kg2,..\fact_physics,..\fact_math
python.exe pysrc\check.py --roots %ROOTS% --all
