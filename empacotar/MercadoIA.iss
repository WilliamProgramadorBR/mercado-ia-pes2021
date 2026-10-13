; Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
; Instalador do Mercado IA (Inno Setup 6). Gerado pelo empacotar\montar.py:
;   ISCC /DVersao=0.9.0 /DPacote=...\dist\MercadoIA /O...\dist MercadoIA.iss
; Instala na pasta do usuário (sem pedir administrador). Reinstalar/atualizar NÃO apaga os dados da carreira
; (app\cerebro\historico, config.json, ia.json): o instalador só substitui os arquivos do programa.

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Pacote
  #define Pacote "..\dist\MercadoIA"
#endif

[Setup]
AppId={{8C5E2A41-6B1F-4E0B-9C3D-4D2F7A1B9E60}
AppName=Mercado IA
AppVersion={#Versao}
AppVerName=Mercado IA {#Versao}
AppPublisher=Mercado IA (comunidade PES 2021)
AppPublisherURL=https://github.com/WilliamProgramadorBR/mercado-ia-pes2021
DefaultDirName={localappdata}\Programs\MercadoIA
DefaultGroupName=Mercado IA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=MercadoIA-Setup-{#Versao}
SetupIconFile={#Pacote}\app\painel\icone.ico
UninstallDisplayIcon={app}\app\painel\icone.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktop"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
Name: "iniciar"; Description: "Abrir o Painel junto com o Windows (minimizado na bandeja)"; GroupDescription: "Opções:"; Flags: unchecked

[Files]
Source: "{#Pacote}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\app\cerebro\historico"

[Icons]
Name: "{group}\Mercado IA"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-s -m painel"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\painel\icone.ico"
Name: "{group}\Manual do Mercado IA"; Filename: "{app}\app\docs\MANUAL.md"
Name: "{group}\Desinstalar o Mercado IA"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Mercado IA"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-s -m painel"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\painel\icone.ico"; Tasks: desktop
Name: "{userstartup}\Mercado IA"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-s -m painel --minimizado"; WorkingDir: "{app}\app"; IconFilename: "{app}\app\painel\icone.ico"; Tasks: iniciar

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: "-s -m painel"; WorkingDir: "{app}\app"; Description: "Abrir o Mercado IA agora"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('O Mercado IA precisa do PES 2021 (PC) com o SIDER instalado — é o Sider que carrega o módulo do Mercado IA dentro do jogo.' + #13#10 + #13#10 +
         'Depois de instalar, o Painel abre na tela de Configuração: ele encontra o jogo e os saves, confere o Sider e instala o módulo para você.' + #13#10 + #13#10 +
         'Faça um backup da pasta de saves antes do primeiro uso.', mbInformation, MB_OK);
end;
