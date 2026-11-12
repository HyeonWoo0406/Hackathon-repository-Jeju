$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'UI build failed' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile --name weekly-report --add-data 'frontend/dist;frontend/dist' --add-data 'backend/app/settings.json;backend/app' --add-data 'backend/app/data;backend/app/data' run.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
