@echo off
chcp 65001 >nul

REM Edite estes caminhos para a sua instalação.
set "PES2021_GAME_DIR=C:\Games\eFootball PES 2021"
set "PES2021_SAVE_DIR=%USERPROFILE%\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\SEU_STEAM_ID\save"
set "MERCADO_IA_TOOLS_DIR=C:\Games\Ferramentas"

start "Mercado IA - vigia" /min python "%~dp0cerebro\vigia.py"
echo Vigia iniciado. Abra o PES 2021 pelo seu launcher habitual.
