@echo off
rem Gunluk urun taramasi (Windows Gorev Zamanlayici bunu calistirir)
cd /d "%~dp0"
if not exist cikti\gunluk mkdir cikti\gunluk
set PYTHONIOENCODING=utf-8
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe" -W ignore gunluk.py %* >> cikti\gunluk\log.txt 2>&1
