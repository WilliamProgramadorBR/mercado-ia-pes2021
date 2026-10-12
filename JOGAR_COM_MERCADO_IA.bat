@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Abre o vigia do Mercado IA (minimizado), a Central do Técnico (minimizada) e o jogo pelo WORLD LAUNCHER.
REM A Central abre no navegador: arraste a janela para o segundo monitor.
start "Mercado IA - vigia" /min python "cerebro\vigia.py"
start "Central do Tecnico" /min python "cerebro\central.py"
start "" /D "..\eFootball PES 2021" "WORLD LAUNCHER.exe"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8765"
