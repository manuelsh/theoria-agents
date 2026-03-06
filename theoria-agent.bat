@echo off
REM Wrapper script for theoria-agent on Windows
REM Sets UTF-8 encoding to fix litellm JSON loading issues
set PYTHONUTF8=1
python -m src.entry %*
