$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& "C:\Users\ASUS\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m ba_monitor
