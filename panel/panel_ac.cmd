@echo off
rem E-ticaret panelini (calismiyorsa) arka planda baslatir ve tarayicida acar.
cd /d "%~dp0"
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8765/api/genel | Out-Null } catch { Start-Process -WindowStyle Hidden -FilePath 'C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe' -ArgumentList 'sunucu.py' -WorkingDirectory '%~dp0.'; Start-Sleep -Seconds 3 }"
start "" http://127.0.0.1:8765
