@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Fecha o vigia travado (se houver) e abre de novo, com o jogo aberto. Ele recupera sozinho a rodada que ficou sem reunião.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.CommandLine -like '*vigia.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
start "Mercado IA - vigia" /min python "cerebro\vigia.py"
