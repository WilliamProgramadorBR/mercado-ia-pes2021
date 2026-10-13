# Empacotar o Mercado IA (para desenvolvedores)

O pacote leva o **Python oficial embutido** (*embeddable package* do python.org), com o **PySide6 (Qt6)** e o Pillow instalados dentro dele. O jogador não instala nada.

Não usamos PyInstaller: um .exe gerado por ele costuma ser barrado pelo antivírus, e este mod já escreve na memória do jogo. Com o Python oficial, os executáveis são os assinados pela Python Software Foundation.

## Estrutura do pacote

```text
MercadoIA\
├─ runtime\          Python embutido + PySide6 + Pillow
│  └─ python3XX._pth   sys.path: o próprio runtime, Lib\site-packages, ..\app e ..\app\cerebro
├─ app\
│  ├─ painel\        o aplicativo Qt6 (python -m painel)
│  ├─ cerebro\       motor, Central, rede neural (sem historico/, ia.json, saves)
│  │  └─ modelos\    modelo inicial da rede dos jogos simulados
│  ├─ sider\MercadoIA.lua
│  ├─ pesXdecrypter\ decrypter21.exe, encrypter21.exe e a licença (versão oficial 6.0.0)
│  ├─ docs\
│  └─ config.json    criado pelo Painel (pastas do jogo, saves, decrypter)
└─ Mercado IA.cmd    atalho da versão portátil
```

O Painel roda em `runtime\pythonw.exe -m painel`, sem console. Os serviços (vigia e Central) rodam em `runtime\python.exe` como processos filhos (`QProcess`), sem janela e com o registro capturado. As variáveis que o Painel passa aos serviços:

| Variável | Para quê |
|---|---|
| `MERCADO_IA_TOOLS_DIR` | a pasta `app` (o motor acha config, backups e save_work por ela) |
| `MERCADO_IA_PAINEL=1` | o motor sabe que o Painel cuida dos processos (a Central não abre vigia em console) |
| `MERCADO_IA_SEM_JANELA=1` | programas auxiliares (decrypter, tasklist, reunião) sem janela piscando |

As pastas do jogo, dos saves e do pesXdecrypter vêm do `cerebro\caminhos.py`. A ordem de prioridade é: variável de ambiente, depois `config.json`, depois o padrão antigo e a detecção automática (Steam, Documentos e OneDrive).

## Gerar

```powershell
python empacotar\montar.py
```

O script:

1. baixa o Python embutido da **mesma versão** do Python que roda o script;
2. instala o PySide6 e o Pillow com `pip --target` (rodas `win_amd64` da mesma versão);
3. tira as partes do Qt que o Painel não usa;
4. copia `painel`, `cerebro` (sem dados pessoais) e `sider`;
5. **para** se encontrar algum segredo (`ia.json`, `*.db` ou chave `AIza...`);
6. embute o **pesXdecrypter 6.0.0** (`app\pesXdecrypter`, com a licença em `empacotar\terceiros`). Ele usa a cópia local se a impressão digital SHA-256 conferir; senão baixa o `.7z` oficial uma vez, para `empacotar\_cache`, e confere;
7. gera o ícone e a versão portátil;
8. gera o instalador, se o **Inno Setup 6** estiver instalado:

```powershell
winget install JRSoftware.InnoSetup
```

Saída em `dist\`: `MercadoIA\` (pasta pronta), `MercadoIA-portatil-<versão>.zip` e `MercadoIA-Setup-<versão>.exe`.

A versão do pacote vem de `painel\base.py` (`VERSAO`).
