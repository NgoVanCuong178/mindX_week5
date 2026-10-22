# Chạy một lượt workflow - dùng cho Windows Task Scheduler (mỗi 2 phút).
# Log của từng lượt nối vào logs\poller-scheduler.log; quyết định chi tiết ở logs\automation.jsonl.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path "$root\logs" | Out-Null
& "$root\.venv\Scripts\python.exe" -m automation.entrypoints.poller --once *>> "$root\logs\poller-scheduler.log"
