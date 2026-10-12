@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Abre só a Central do Técnico (sem o jogo). Para atualizar os dados sem jogar, rode o vestiario.py.
start "Central do Tecnico" /min python "cerebro\central.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"
