@echo off
cd /d "%~dp0"
python -m pytest tests\test_dual_apps.py -q
pause
