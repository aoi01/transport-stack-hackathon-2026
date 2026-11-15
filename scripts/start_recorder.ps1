# GTFS-RT の記録を起動する（PowerShell）。リポジトリ直下で実行する。
# 例: powershell -ExecutionPolicy Bypass -File scripts\start_recorder.ps1
# ログ: data\raw\gtfs_rt\recorder.log
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = "src"
python -X utf8 -m tsh.recorder
