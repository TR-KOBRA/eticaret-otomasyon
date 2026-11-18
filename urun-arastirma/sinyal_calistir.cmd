@echo off
rem Otomatik urun sinyali (Windows Gorev Zamanlayici bunu calistirir: Pzt ve Per 09:00)
cd /d "%~dp0"
if not exist cikti\sinyal mkdir cikti\sinyal
set PYTHONIOENCODING=utf-8
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe" -W ignore sinyal.py --kac 2 --adet 30 --dogrula 3 --trendyol-adet 20 %* >> cikti\sinyal\log.txt 2>&1
